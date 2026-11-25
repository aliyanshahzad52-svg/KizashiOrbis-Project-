"""Upscale chosen destination photos x4 (Real-ESRGAN, tiled), light polish. Usage: upscale.py <model> <out_dir> name=path ..."""
import sys
import cv2
import numpy as np
import onnxruntime as ort
M, OUT = sys.argv[1:3]
sr = ort.InferenceSession(M, providers=["CPUExecutionProvider"]); IN = sr.get_inputs()[0].name
T, O = 128, 10; ST = T - 2 * O
r = np.linspace(0.02, 1, O * 8); ramp = np.ones(T * 4, np.float32); ramp[:len(r)] = r; ramp[-len(r):] = r[::-1]
WT = (ramp[:, None] * ramp[None, :])[..., None]
for a in sys.argv[3:]:
    name, p = a.split("=")
    f = cv2.imread(p); h, w = f.shape[:2]
    ys = list(range(0, h - T, ST)) + [h - T]; xs = list(range(0, w - T, ST)) + [w - T]
    img = f[:, :, ::-1].astype(np.float32) / 255
    out = np.zeros((h * 4, w * 4, 3), np.float32); ws = np.zeros((h * 4, w * 4, 1), np.float32)
    for y in ys:
        for x in xs:
            o = sr.run(None, {IN: np.ascontiguousarray(img[y:y + T, x:x + T].transpose(2, 0, 1)[None])})[0][0].transpose(1, 2, 0)
            out[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += o * WT; ws[y * 4:(y + T) * 4, x * 4:(x + T) * 4] += WT
    up = np.clip(out / ws, 0, 1)[:, :, ::-1]
    up = cv2.resize(up, (1152, 2048), interpolation=cv2.INTER_AREA)
    lz = cv2.resize(f, (1152, 2048), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
    g = 0.8 * up + 0.2 * lz
    hsv = cv2.cvtColor(g, cv2.COLOR_BGR2HSV); hsv[..., 1] = np.clip(hsv[..., 1] * 1.06, 0, 1); g = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    cv2.imwrite(f"{OUT}/{name}.jpg", np.clip(g * 255 + .5, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 94])
    print("wrote", name, flush=True)
