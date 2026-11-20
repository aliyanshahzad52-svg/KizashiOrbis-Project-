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
    (62.66, 66.22, "ur", "because Italy rule: *first come and first serve.*"),
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


# Roman word -> Urdu word index map where the counts differ:
#   k = same word, (a, b) = spans Urdu words a..b, (k, j, n) = j-th of n parts of Urdu word k
UR_MAP = {
    11.08: [(0, 1), 2, 3, 4, 5, 6, 7, 8],
    26.86: [0, 1, (2, 3), 4, 5, 6, 7, 8],
    44.84: [0, (1, 0, 2), (1, 1, 2), (2, 4), 5],
    53.62: [0, (1, 3), 4, 5, 6, 7, 8, 9, 10, 11, 12],
    59.62: [0, 1, 2, 3, (4, 5), 6, 7],
    62.66: [0, 1, 2, 3, 4, 5, (6, 0, 2), (6, 1, 2)],
    66.22: [(0, 0, 2), (0, 1, 2)],
}
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
        mp = UR_MAP.get(a)
        if a == 34.55:                            # "Is ke" sits just before the first Urdu word kept
            toks[0]["s"], toks[0]["e"] = 34.55, 34.64
            toks[1]["s"], toks[1]["e"] = 34.64, 34.74
            for tk, w in zip(toks[2:], src[-13:]):
                tk["s"], tk["e"] = w["s"], w["e"]
            words += toks
            continue
        if mp:
            for tk, m in zip(toks, mp):
                if m is None:
                    continue
                if isinstance(m, int):
                    tk["s"], tk["e"] = src[m]["s"], src[m]["e"]
                elif len(m) == 2:
                    tk["s"], tk["e"] = src[m[0]]["s"], src[m[1]]["e"]
                else:
                    k, j, n = m
                    d = (src[k]["e"] - src[k]["s"]) / n
                    tk["s"], tk["e"] = src[k]["s"] + j * d, src[k]["s"] + (j + 1) * d
            words += toks
            continue
        if len(src) == len(toks):                 # word-for-word transliteration: exact timings
            for tk, w in zip(toks, src):
                tk["s"], tk["e"] = w["s"], w["e"]
            words += toks
            continue
        print("proportional timing:", text[:40], len(src), "urdu vs", len(toks), "roman")
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


# ------------------------------------------------ v2 design: typography, graphics, sound
ALLW = words


def w_at(text, after=0.0):
    """Output time of the first spoken word `text` at/after `after` (output seconds)."""
    for w in ALLW:
        if w["text"].strip(".,?:").lower() == text.lower() and w["os"] >= after - 1e-6:
            return w["os"]
    raise KeyError(text)


T = {k: w_at(*v) if isinstance(v, tuple) else w_at(v) for k, v in {
    "study": "study", "europe": "Europe", "expensive": "expensive", "tuition": ("tuition", 3),
    "living": "living", "italy1": "Italy", "aliyan": "Aliyan", "excellent": "excellent",
    "fee": ("fee", 19), "fully": "fully", "seven": "7,000", "ten": "10,000", "accom": "accommodation",
    "food": ("food", 30), "documents": "documents", "complete": "complete", "contact": ("contact", 39),
    "orbis2": ("OrbisNexa", 40), "profile": "profile", "eligible": "eligible", "september": "September",
    "y2027": "2027", "applications": "applications", "open": "open", "soon": "soon",
    "possible": "possible", "firstcome": ("first", 59), "thank": "Thank"}.items()}

# big kinetic typography placed on the wall BEHIND the speaker (occluded by the person matte)
BACK = [
    {"t0": 0.0, "t1": 2.62, "lines": [["STUDY IN", "s"], ["EUROPE?", "xl", T["europe"]]], "flag": ["eu", T["europe"]]},
    {"t0": T["expensive"] - 0.1, "t1": 6.32, "lines": [["TOO", "m"], ["EXPENSIVE?", "xl", T["expensive"]]]},
    {"t0": T["italy1"] - 0.08, "t1": 8.78, "lines": [["THEN", "s"], ["ITALY", "xxl", T["italy1"]]], "flag": ["it", T["italy1"]]},
    {"t0": T["aliyan"] - 0.12, "t1": 12.25, "lines": [["ALIYAN SHAHZAD", "l"], ["ORBISNEXA CONSULTANCY", "s", T["aliyan"] + 0.5]]},
    {"t0": T["excellent"] - 0.08, "t1": 18.70, "lines": [["EXCELLENT", "l"], ["OPTION", "m", T["excellent"] + 0.35]]},
    {"t0": T["fee"] - 0.06, "t1": 21.98, "lines": [["TUITION FEE", "s"], ["€0", "xxl", T["fee"]]], "accent": "gold"},
    {"t0": T["fully"] - 0.06, "t1": 23.36, "lines": [["FULLY", "l"], ["FUNDED", "m", T["fully"] + 0.25]]},
    {"t0": T["seven"] - 0.25, "t1": 30.62, "lines": [["UP TO", "s"], ["€COUNT", "xxl", T["seven"]]], "accent": "gold",
     "count": [[T["seven"], 0, 7000, 1.15], [T["ten"], 7000, 10000, 1.0]], "after": [T["ten"], "ANNUAL STIPEND"]},
    {"t0": T["accom"] - 0.08, "t1": 34.58, "lines": [["+ ACCOMMODATION", "m"], ["+ FOOD", "l", T["food"]]]},
    {"t0": T["documents"] - 0.08, "t1": 37.0, "lines": [["COMPLETE", "s", T["complete"]], ["DOCUMENTS?", "l"]]},
    {"t0": T["contact"] - 0.05, "t1": 42.20, "lines": [["CONTACT", "s"], ["ORBISNEXA", "xl", T["orbis2"]]]},
    {"t0": T["profile"] - 0.08, "t1": 45.95, "lines": [["PROFILE", "l"], ["ASSESSMENT", "m", T["profile"] + 0.5]]},
    {"t0": T["eligible"] - 0.08, "t1": 48.62, "lines": [["ELIGIBLE?", "xl"]]},
    {"t0": T["september"] - 0.06, "t1": 52.40, "lines": [["SEPTEMBER", "m"], ["2027", "xxl", T["y2027"]], ["INTAKE", "s", T["y2027"] + 0.5]], "accent": "gold"},
    {"t0": T["applications"] - 0.08, "t1": 54.38, "lines": [["APPLICATIONS", "m"], ["OPEN", "xxl", T["open"]]], "accent": "green"},
    {"t0": T["soon"] - 0.25, "t1": 57.40, "lines": [["APPLY", "l"], ["ASAP", "xxl", T["possible"]]]},
    {"t0": T["firstcome"] - 0.08, "t1": 61.0, "lines": [["FIRST COME,", "l"], ["FIRST SERVE", "m", T["firstcome"] + 0.92]]},
]

# animated graphics in FRONT of the speaker (right-hand column over the wall)
FRONT = [
    {"kind": "cashout", "t0": T["expensive"], "t1": 6.30},
    {"kind": "zero", "t0": T["fee"], "t1": 21.95},
    {"kind": "cap", "t0": T["fully"], "t1": 23.35},
    {"kind": "coins", "t0": T["seven"] - 0.1, "t1": 30.6, "steps": [[T["seven"], 7000, 1.15], [T["ten"], 10000, 1.0]]},
    {"kind": "icons", "t0": T["accom"] - 0.05, "t1": 34.55, "items": [["home", T["accom"]], ["food", T["food"]]]},
    {"kind": "doc", "t0": T["documents"], "t1": 36.95, "check": T["complete"]},
    {"kind": "scan", "t0": T["profile"], "t1": 45.9},
    {"kind": "check", "t0": T["eligible"], "t1": 48.6},
    {"kind": "calendar", "t0": T["september"], "t1": 52.35},
    {"kind": "live", "t0": T["open"] - 0.1, "t1": 54.35},
    {"kind": "clock", "t0": T["soon"], "t1": 57.35},
]

# sound design, synced to the same instants
SFX = [
    ["whoosh_in", 0.02, 0.5], ["impact_soft", T["europe"], 0.45],
    ["whoosh", T["expensive"] - 0.12, 0.45], ["cash_flutter", T["tuition"], 0.55], ["cash_flutter", T["living"], 0.45],
    ["impact_soft", T["italy1"], 0.55], ["swoosh_up", T["aliyan"] - 0.25, 0.35],
    ["shimmer", T["excellent"], 0.35],
    ["stamp", T["fee"] + 0.05, 0.6], ["sparkle", T["fully"], 0.5],
    ["chaching", T["seven"] + 1.12, 0.6], ["chaching", T["ten"] + 0.98, 0.7], ["rise", T["ten"] - 0.05, 0.35],
    ["pop", T["accom"], 0.5], ["pop", T["food"], 0.5],
    ["tick", T["complete"] + 0.05, 0.55], ["whoosh", T["contact"] - 0.1, 0.35], ["impact_soft", T["orbis2"], 0.45],
    ["scan", T["profile"], 0.35], ["ding", T["eligible"] + 0.15, 0.5],
    ["page", T["september"], 0.5], ["impact_soft", T["y2027"], 0.4], ["ping", T["open"], 0.55],
    ["whoosh", T["soon"] - 0.2, 0.35], ["impact_soft", T["firstcome"], 0.4],
    ["whoosh_in", VIDEO_LEN - 0.25, 0.5], ["shimmer", VIDEO_LEN + 0.5, 0.45],
]
for k in range(1, 9):                                      # coins clinking while the counters run
    SFX.append(["coin", T["seven"] + 0.05 + k * 0.13, 0.28])
for k in range(1, 7):
    SFX.append(["coin", T["ten"] + 0.05 + k * 0.15, 0.3])

# zoom-blur "punch" transitions on the emphasis cuts (output time of the cut)
PUNCH = [round(sh["t0"], 3) for sh in shots if sh["trans"] == "cut" and sh["zoom"] >= 1.24 and sh["t0"] > 0]
for t in PUNCH:
    SFX.append(["punch", t - 0.04, 0.22])

json.dump({"edl": EDL, "video_len": round(VIDEO_LEN, 3), "end_card": END_CARD, "duration": DURATION,
           "shots": shots, "captions": captions, "back": BACK, "front": FRONT, "sfx": SFX, "punch": PUNCH, "T": T},
          open("edit.json", "w"), indent=1, ensure_ascii=False)
print("duration", DURATION, "captions", len(captions), "shots", len(shots))
for c in captions[:60]:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f}  " + " ".join(("[" + w["text"] + "]") if w["key"] else w["text"] for w in c["words"]))
