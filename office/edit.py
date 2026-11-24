"""Edit decision list for the OrbisNexa office promo (1920x1080, 23.976 fps).

Each shot: source clip, source in/out, slow push-in (zoom from z0 to z1 about a focus point),
transition into the shot ("cut", "flash" = white zoom-blur flash, "punch" = short zoom-blur punch),
and one block of large promotional background text (rendered behind the people).
Text block: centre (cx, cy) in output px, lines of [text, style] where style is
  "s"  small light lowercase word            (reference: "same", "and", "for")
  "b"  big bold navy word                     (reference: "neighborhood", "record")
  "g"  big bold OrbisNexa gradient word       (reference: gold "17", "marketing", "vendor")
"""
import json

UP = "/root/.claude/uploads/58419071-33a5-5774-82e8-3e5c766ce9cc/"
C1 = UP + "617b202b-e08757b8-2463-4931-b7f5-e234117a6209.mp4"      # consultant, medium
C2 = UP + "d96df676-df5104e2-30e8-4ccf-953f-5b6e163a4126.mp4"      # student close-up
C3 = UP + "90e7021b-b5347d1a-8c2c-4862-8391-a20f0c824b2f.mov"      # student (back) + consultant, wide
C4 = UP + "07a8bff2-2c9eb405-07af-467c-a040-3f4421bf0537.mov"      # second student + consultant / close-up
C5 = UP + "f570a5f6-2c9eb405-07af-467c-a040-3f4421bf0537.mov"      # second student + consultant, other angle

FPS = 24000 / 1001

SHOTS = [
    dict(src=C2, a=1.0, b=5.0, z=(1.00, 1.05), f=(820, 380), tr="cut",
         text=dict(cx=1520, cy=360, mw=700, lines=[["APPLICATIONS", "g"], ["are now", "s"], ["OPEN!", "b"]])),
    dict(src=C3, a=0.6, b=4.6, z=(1.00, 1.06), f=(1350, 330), tr="flash",
         text=dict(cx=955, cy=300, mw=520, lines=[["your", "s"], ["FUTURE", "g"], ["starts here", "s"]])),
    dict(src=C1, a=2.0, b=5.6, z=(1.04, 1.09), f=(1000, 380), tr="punch",
         text=dict(cx=1445, cy=280, mw=520, lines=[["expert", "s"], ["GUIDANCE", "b"]])),
    dict(src=C4, a=0.8, b=4.8, z=(1.00, 1.05), f=(1220, 300), tr="cut",
         text=dict(cx=940, cy=270, mw=400, lines=[["study", "s"], ["ABROAD", "g"]])),
    dict(src=C2, a=6.0, b=9.6, z=(1.03, 1.08), f=(820, 380), tr="flash",
         text=dict(cx=1520, cy=380, mw=700, lines=[["FULLY FUNDED", "g"], ["scholarships", "s"], ["AVAILABLE", "b"]])),
    dict(src=C5, a=3.0, b=6.6, z=(1.00, 1.05), f=(1380, 300), tr="cut",
         text=dict(cx=870, cy=250, mw=600, lines=[["TOP", "g"], ["universities", "s"], ["worldwide", "s"]])),
    dict(src=C4, a=13.6, b=17.6, z=(1.00, 1.05), f=(1170, 360), tr="punch",
         text=dict(cx=630, cy=300, mw=620, lines=[["book your", "s"], ["FREE", "g"], ["CONSULTATION", "b"]])),
    dict(src=C1, a=11.0, b=14.5, z=(1.03, 1.08), f=(1030, 400), tr="cut",
         text=dict(cx=1445, cy=280, mw=500, lines=[["every", "s"], ["STEP", "b"], ["of the way", "s"]])),
    dict(src=C3, a=11.4, b=14.9, z=(1.00, 1.05), f=(1350, 300), tr="flash",
         text=dict(cx=960, cy=300, mw=500, lines=[["dream", "s"], ["BEYOND", "g"], ["the map", "s"]])),
    dict(src=C4, a=5.6, b=10.0, z=(1.00, 1.06), f=(1450, 330), tr="cut",
         text=dict(cx=850, cy=280, mw=680, lines=[["start your", "s"], ["INTERNATIONAL", "g"], ["EDUCATION", "b"], ["journey today.", "s"]])),
]
END = 6.2                      # end card length (logo travels to centre, contacts)
TAIL = 1.2                     # last shot keeps playing (blurred) this long under the end card start

t = 0.0
for s in SHOTS:
    s["t0"] = round(t, 4)
    t += s["b"] - s["a"]
    s["t1"] = round(t, 4)
VIDEO = t
SHOTS[-1]["b"] += TAIL         # footage continues under the end card
DUR = VIDEO + END
json.dump(dict(fps=FPS, shots=SHOTS, video=VIDEO, end=END, duration=DUR), open("edit.json", "w"), indent=1)
print(f"video {VIDEO:.2f}s + end {END}s = {DUR:.2f}s")
