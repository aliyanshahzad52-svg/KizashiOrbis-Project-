"""Generate original photographic backgrounds with SDXL-Turbo (ONNX, CPU) - no stock footage reused.

Usage: python3 gen_bg.py <sdxl_turbo_onnx_dir> <clip_tokenizer.json> <out_dir> [name ...]
"""
import os
import sys
import time

import numpy as np
import onnxruntime as ort
from PIL import Image
from tokenizers import Tokenizer

MD, TOK, OUT = sys.argv[1:4]
ONLY = set(sys.argv[4:])
os.makedirs(OUT, exist_ok=True)
H, W = 1024, 576                     # portrait, multiples of 64
STEPS = 4

NEG = ""
SCENES = {
    "booth": "a classic red telephone box on a quiet London street, Victorian terraced buildings behind, "
             "overcast soft daylight, cinematic photograph, 35mm lens, shallow depth of field, highly detailed, sharp focus",
    "library": "a young university student reading a book at a wooden desk in a grand old university library, "
               "tall bookshelves in the background, warm window light, cinematic photograph, 50mm, detailed, realistic",
    "college": "gothic stone university college building in England, tall arched windows and spires, low angle view, "
               "dramatic sky, cinematic architectural photograph, highly detailed, realistic",
    "gate": "grand entrance gate of a British university campus, stone pillars with ornate black iron gates, "
            "red brick building behind, trimmed hedges, overcast daylight, cinematic photograph, realistic, detailed",
}

so = ort.SessionOptions()
so.intra_op_num_threads = 4
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
so.enable_cpu_mem_arena = False
so.enable_mem_pattern = False
so.add_session_config_entry("session.disable_prepacking", "1")       # prepacking would duplicate the 10 GB of weights
P = ["CPUExecutionProvider"]
te1 = ort.InferenceSession(f"{MD}/text_encoder/model.onnx", so, providers=P)
te2 = ort.InferenceSession(f"{MD}/text_encoder_2/model.onnx", so, providers=P)
tok = Tokenizer.from_file(TOK)


def ids(text, pad):
    t = tok.encode(text).ids                      # includes BOS/EOS from the CLIP post-processor
    if t[0] != 49406:
        t = [49406] + t
    if t[-1] != 49407:
        t = t + [49407]
    t = t[:77]
    t[-1] = 49407
    return np.array([t + [pad] * (77 - len(t))], np.int64)


def run(sess, x):
    name = sess.get_inputs()[0]
    dt = np.int32 if "int32" in name.type else np.int64
    outs = sess.run(None, {name.name: x.astype(dt)})
    return dict(zip([o.name for o in sess.get_outputs()], outs))


def encode(text):
    o1 = run(te1, ids(text, 49407))
    o2 = run(te2, ids(text, 0))
    h1 = o1.get("hidden_states.11")                 # penultimate layer of CLIP-L (12 layers)
    h2 = o2.get("hidden_states.31")                 # penultimate layer of OpenCLIP-bigG (32 layers)
    pooled = o2.get("text_embeds")
    return np.concatenate([h1, h2], -1).astype(np.float32), pooled.astype(np.float32)


print("text encoders io:", [o.name for o in te2.get_outputs()][:4], flush=True)
emb = {k: encode(v) for k, v in SCENES.items() if not ONLY or k in ONLY}
del te1, te2

unet = ort.InferenceSession(f"{MD}/unet/model.onnx", so, providers=P)
vae = ort.InferenceSession(f"{MD}/vae_decoder/model.onnx", so, providers=P)
UIN = {i.name: i for i in unet.get_inputs()}
print("unet inputs:", {k: (v.type, v.shape) for k, v in UIN.items()}, flush=True)

betas = np.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000) ** 2
ac = np.cumprod(1 - betas)
ts = np.array([999, 749, 499, 249])[:STEPS]                # trailing spacing
sig = np.sqrt((1 - ac[ts]) / ac[ts])
sig = np.append(sig, 0.0)
time_ids = np.array([[H, W, 0, 0, H, W]], np.float32)


def unet_eps(lat, t, eh, te):
    feed = {"sample": lat.astype(np.float32), "encoder_hidden_states": eh, "text_embeds": te, "time_ids": time_ids}
    tt = UIN["timestep"]
    feed["timestep"] = np.array([t] if tt.shape and tt.shape != [] else t,
                                np.float32 if "float" in tt.type else np.int64)
    return unet.run(None, feed)[0]


for name, (eh, te) in emb.items():
    for seed in (1, 2):
        rng = np.random.default_rng(seed * 101 + len(name))
        x = rng.standard_normal((1, 4, H // 8, W // 8)).astype(np.float32) * sig[0]
        t0 = time.time()
        for k, t in enumerate(ts):                           # Euler ancestral
            s = sig[k]
            eps = unet_eps(x / np.sqrt(s * s + 1), t, eh, te)
            x0 = x - s * eps
            s_next = sig[k + 1]
            s_up = np.sqrt(max(s_next ** 2 * (s * s - s_next ** 2) / (s * s), 0))
            s_down = np.sqrt(max(s_next ** 2 - s_up ** 2, 0))
            x = x0 + (x - x0) / s * s_down if s_down > 0 else x0
            if s_up > 0:
                x = x + rng.standard_normal(x.shape).astype(np.float32) * s_up
        img = vae.run(None, {vae.get_inputs()[0].name: (x / 0.13025).astype(np.float32)})[0][0]
        img = np.clip((img.transpose(1, 2, 0) + 1) * 127.5, 0, 255).astype(np.uint8)
        Image.fromarray(img).save(f"{OUT}/{name}_{seed}.png")
        print(f"{name}_{seed}  {time.time() - t0:.0f}s", flush=True)
