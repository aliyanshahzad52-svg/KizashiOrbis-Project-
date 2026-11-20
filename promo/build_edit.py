"""Build the edit decision list, shot plan and timed captions for the Italy talking-head promo.

Inputs : transcript.json (Whisper large-v3, Urdu, word timestamps), head.json (opening 15 s, en/ur)
Output : edit.json  {edl, shots, captions, events, duration}

Captions are written in Roman Urdu with English terms kept in English (how the
speaker actually talks). Word timings come from Whisper; for Urdu segments the
Roman words are spread across the Urdu word timings by character position.
Words wrapped in *asterisks* are key phrases and get the brand highlight.
"""
import json
import re

T = json.load(open("transcript.json"))
HEAD = json.load(open("head.json"))

# ---------------------------------------------------------------- edit list
# source ranges kept: jump cuts remove dead air (1.8 s after "but"), a filler "aah" and breaths
EDL = [(0.00, 2.70), (4.42, 8.12), (8.62, 22.50), (23.05, 23.55), (24.25, 34.15), (34.55, 38.56),
       (39.10, 42.62), (43.12, 57.36), (57.66, 66.95)]


def src_to_out(t):
    acc = 0.0
    for a, b in EDL:
        if t < a:
            return acc
        if t <= b:
            return acc + (t - a)
        acc += b - a
    return acc


VIDEO_LEN = sum(b - a for a, b in EDL)
END_CARD = 4.6
DURATION = round(VIDEO_LEN + END_CARD, 3)

# ------------------------------------------------------------- caption text
# (segment start, end, roman text) in source time; segments come from Whisper
ROMAN = [
    (0.00, 8.04, "en", "Are you planning to study in *Europe* but worried about *expensive tuition fees* and *living costs?*"),
    (8.60, 11.02, "en", "Then *Italy* could be the *right option* for you."),
    (11.08, 14.46, "ur", "Assalam-o-Alaikum, main *Aliyan Shahzad* hoon, from *OrbisNexa Consultancy.*"),
    (14.56, 20.98, "ur", "Agar aap *Italy* mein study karna chah rahe hain, to Italy aap ke liye ek *excellent option* ho sakta hai,"),
    (20.98, 26.86, "manual", "kyunki yahan pe na to aap ko *fee* university ki deni hai, *fully funded scholarships* hain,",
     [(20.98, 21.32), (21.32, 21.58), (21.58, 21.72), (21.72, 21.92), (21.92, 22.08), (22.08, 22.24), (22.24, 22.48),
      (23.10, 23.50), (24.30, 24.95), (25.04, 25.14), (25.14, 25.36), (25.36, 25.52), (25.52, 25.76), (25.76, 26.10),
      (26.10, 26.74), (26.74, 26.86)]),
    (26.86, 30.30, "ur", "*up to 7,000 euros* ka *annual stipend* hai,"),
    (30.70, 34.15, "manual", "and some universities offer *10,000 euros* annual stipend.",
     [(30.76, 30.90), (30.90, 31.14), (31.14, 31.62), (31.64, 32.08), (32.12, 32.80), (32.82, 33.10), (33.12, 33.58), (33.60, 34.10)]),
    (34.55, 38.50, "ur", "Is ke saath saath aap ko *accommodation* aur *food* bhi kuch universities offer karti hain."),
    (38.50, 44.84, "ur", "Agar aap ke *documents complete* hain, but aap worried hain ke apna process kis se karwayein,"),
    (44.84, 47.20, "ur", "to contact karein *OrbisNexa Consultancy.*"),
    (47.20, 51.06, "ur", "Hum aap ki *profile ki assessment* karne ke baad aap ko bata dein ge,"),
    (51.06, 53.62, "ur", "agar aap *eligible* hain to aap ka apply ho sakta hai."),
    (53.62, 57.22, "ur", "*September 2027 intake* ke liye agar aap apply karna chahte hain,"),
    (57.76, 59.62, "ur", "universities ki *applications open* hain."),
    (59.62, 62.66, "ur", "So *as soon as possible* apply karein,"),
    (62.66, 66.22, "ur", "because Italy rule: *first come, first serve.*"),
    (66.22, 66.82, "ur", "Thank you."),
]


def urdu_words_between(a, b):
    out = []
    for s in T["segments"]:
        for w in s["words"]:
            if w["s"] >= a - 0.05 and w["e"] <= b + 0.05:
                out.append(w)
    if not out:   # opening Urdu greeting lives in head.json
        for s in HEAD["ur"]:
            for w in s["words"]:
                if w["s"] >= a - 0.05 and w["e"] <= b + 0.05:
                    out.append(w)
    return out


def en_words_between(a, b):
    return [w for s in HEAD["en"] for w in s["words"] if w["s"] >= a - 0.05 and w["e"] <= b + 0.05]


def tokens(text):
    """Split into words, tracking *key* spans."""
    out, key = [], False
    for raw in text.split():
        start = raw.startswith("*")
        if start:
            key = True
        word = raw.replace("*", "")
        out.append({"text": word, "key": key})
        if raw.endswith("*") or raw.endswith("*,") or raw.endswith("*.") or raw.endswith("*?") or re.search(r"\*[.,?:]?$", raw):
            key = False
    return out


ROMAN_TIMES = {(r[0], r[1]): r[4] for r in ROMAN if r[2] == "manual"}
ROMAN = [r[:4] for r in ROMAN]

words = []
for a, b, lang, text in ROMAN:
    toks = tokens(text)
    if lang == "manual":
        times = ROMAN_TIMES[(a, b)]
        assert len(times) == len(toks), (text, len(times), len(toks))
        for tk, (ws, we) in zip(toks, times):
            tk["s"], tk["e"] = ws, we
    elif lang == "en":
        src = en_words_between(a, b)
        assert len(src) == len(toks), (text, len(src), len(toks))
        for tk, w in zip(toks, src):
            tk["s"], tk["e"] = w["s"], w["e"]
        for tk in toks:                          # Whisper stretched "worried" over the pause
            if tk["text"] == "worried":
                tk["s"] = 4.45
    else:
        src = urdu_words_between(a, b)
        # cumulative character position -> time, along the Urdu words
        cum, tot = [0.0], 0.0
        for w in src:
            tot += max(len(w["w"].strip()), 1)
            cum.append(tot)
        times = [src[0]["s"]] + [w["e"] for w in src]

        def t_at(frac):
            x = frac * tot
            for k in range(len(src)):
                if cum[k + 1] >= x:
                    f = (x - cum[k]) / max(cum[k + 1] - cum[k], 1e-6)
                    return src[k]["s"] + f * (src[k]["e"] - src[k]["s"])
            return times[-1]

        rlen = sum(len(tk["text"]) + 1 for tk in toks)
        pos = 0
        for tk in toks:
            tk["s"] = t_at(pos / rlen)
            pos += len(tk["text"]) + 1
            tk["e"] = t_at(pos / rlen)
    words += toks

# drop words inside removed ranges (none expected) and map to output time
for w in words:
    w["os"], w["oe"] = round(src_to_out(w["s"]), 3), round(src_to_out(w["e"]), 3)

# ------------------------------------------------------------ caption chunks
chunks, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    chars = sum(len(x["text"]) + 1 for x in cur)
    nxt = words[i + 1] if i + 1 < len(words) else None
    end_punct = w["text"][-1] in ".,?:"
    gap = (nxt["os"] - w["oe"]) if nxt else 9
    if end_punct or chars >= 17 or len(cur) >= 3 or gap > 0.35 or (nxt and nxt["key"] != w["key"] and chars >= 10):
        chunks.append(cur)
        cur = []
if cur:
    chunks.append(cur)
captions = []
for k, c in enumerate(chunks):
    t0 = c[0]["os"]
    t1 = c[-1]["oe"]
    nxt = chunks[k + 1][0]["os"] if k + 1 < len(chunks) else t1 + 0.6
    captions.append({"t0": round(t0, 3), "t1": round(min(max(t1 + 0.12, t0 + 0.45), nxt), 3),
                     "words": [{"text": w["text"], "key": w["key"], "t0": w["os"], "t1": w["oe"]} for w in c]})

# --------------------------------------------------------------- shot plan
# (source start, zoom, transition) - zoom about the face, 'cut' = punch, 'ease' = smooth move
SHOTS = [
    (0.00, 1.24, "cut"),     # hook: close, slow push
    (4.42, 1.00, "cut"),     # jump cut -> wide for the worries card
    (8.62, 1.30, "cut"),     # "Then Italy..." punch in
    (11.08, 1.12, "ease"),   # introduction
    (14.56, 1.00, "ease"),   # Italy as an option, wide breathing room
    (20.98, 1.24, "cut"),    # no tuition fee
    (24.25, 1.10, "cut"),    # jump cut (pause removed)
    (25.52, 1.40, "cut"),    # fully funded scholarships - extreme close-up
    (26.86, 1.12, "cut"),    # 7,000 stipend
    (30.70, 1.26, "cut"),    # 10,000 euros
    (34.55, 1.00, "cut"),    # accommodation + food (jump cut)
    (39.10, 1.24, "cut"),    # documents (jump cut)
    (43.12, 1.12, "cut"),    # jump cut (pause removed)
    (44.84, 1.38, "cut"),    # contact OrbisNexa - punch
    (47.20, 1.00, "cut"),    # assessment
    (53.62, 1.14, "ease"),   # September 2027 intake
    (57.66, 1.28, "cut"),    # applications open, ASAP (jump cut)
    (62.66, 1.12, "cut"),    # first come first serve
]
shots = []
for k, (s, z, tr) in enumerate(SHOTS):
    e = SHOTS[k + 1][0] if k + 1 < len(SHOTS) else 66.95
    shots.append({"t0": round(src_to_out(s), 3), "t1": round(src_to_out(e), 3), "zoom": z, "trans": tr})


def at(src_t):
    return round(src_to_out(src_t), 3)


# ------------------------------------------------ supporting visual events
EVENTS = [
    {"type": "flag", "code": "eu", "label": "EUROPE", "t0": at(1.85), "t1": at(2.69)},
    {"type": "list", "title": "The usual worries", "items": [["fee", "Expensive tuition fees"], ["home", "High living costs"]], "t0": at(5.0), "t1": at(8.1)},
    {"type": "flag", "code": "it", "label": "ITALY", "t0": at(8.85), "t1": at(11.0)},
    {"type": "name", "name": "Aliyan Shahzad", "role": "OrbisNexa Consultancy", "t0": at(11.6), "t1": at(14.4)},
    {"type": "badge", "icon": "uni", "big": "No tuition fee", "small": "at public universities", "t0": at(21.6), "t1": at(24.15)},
    {"type": "badge", "icon": "cap", "big": "Fully funded", "small": "scholarships", "t0": at(24.45), "t1": at(26.8)},
    {"type": "stat", "values": [[at(27.2), 7000], [at(32.1), 10000]], "unit": "€",
     "smalls": [[at(27.2), "annual stipend"], [at(32.1), "at some universities"]], "t0": at(27.0), "t1": at(34.1)},
    {"type": "list", "title": "Offered by some universities", "items": [["home", "Accommodation"], ["food", "Food"]], "t0": at(35.5), "t1": at(38.5)},
    {"type": "badge", "icon": "doc", "big": "Documents ready?", "small": "we handle the process", "t0": at(39.25), "t1": at(44.7)},
    {"type": "badge", "icon": "search", "big": "Profile assessment", "small": "eligibility check", "t0": at(47.6), "t1": at(53.5)},
    {"type": "badge", "icon": "cal", "big": "September 2027", "small": "intake", "t0": at(53.8), "t1": at(57.3)},
    {"type": "badge", "icon": "live", "big": "Applications open", "small": "apply as soon as possible", "t0": at(57.8), "t1": at(62.6)},
    {"type": "badge", "icon": "clock", "big": "First come,", "small": "first serve", "t0": at(63.4), "t1": at(66.2)},
]

json.dump({"edl": EDL, "video_len": round(VIDEO_LEN, 3), "end_card": END_CARD, "duration": DURATION,
           "shots": shots, "captions": captions, "events": EVENTS},
          open("edit.json", "w"), indent=1, ensure_ascii=False)
print("duration", DURATION, "captions", len(captions), "shots", len(shots))
for c in captions[:60]:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f}  " + " ".join(("[" + w["text"] + "]") if w["key"] else w["text"] for w in c["words"]))
