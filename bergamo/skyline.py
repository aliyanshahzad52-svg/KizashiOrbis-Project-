"""Generates the Italian landmark line-illustration (SVG) used at the bottom of bergamo_post.html.
viewBox 0 0 1080 272, ground at y=270. Separate, detailed buildings with breathing space between them."""
L = "#1f2655"           # line colour
F = "#e8ebf9"           # main fill
F2 = "#d9def5"          # shaded fill
W = "#f6f8fd"           # openings
out = []
a = out.append


def arch(x, y_base, w, h, fill=W, sw=1.8):
    r = w / 2
    a(f'<path d="M{x:.1f} {y_base:.1f}V{y_base - h + r:.1f}a{r:.1f} {r:.1f} 0 0 1 {w:.1f} 0V{y_base:.1f}z" fill="{fill}" stroke="{L}" stroke-width="{sw}"/>')


def gothic(x, y_base, w, h):
    r = w / 2
    a(f'<path d="M{x:.1f} {y_base:.1f}V{y_base - h + w*0.8:.1f}Q{x:.1f} {y_base - h:.1f} {x + r:.1f} {y_base - h:.1f}Q{x + w:.1f} {y_base - h:.1f} {x + w:.1f} {y_base - h + w*0.8:.1f}V{y_base:.1f}z" fill="{W}" stroke="{L}" stroke-width="1.6"/>')


def line(x1, y1, x2, y2, sw=1.6, c=L):
    a(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{c}" stroke-width="{sw}" fill="none"/>')


def rect(x, y, w, h, fill=F, sw=2.4, rx=0):
    a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{L}" stroke-width="{sw}"/>')


def shadow(cx, w):
    a(f'<ellipse cx="{cx}" cy="270" rx="{w/2}" ry="5" fill="#c8cff0" opacity=".55"/>')


def cypress(x, h, w=16):
    a(f'<path d="M{x} 270c-{w*0.75:.1f}-{h*0.38:.1f}-{w*0.35:.1f}-{h*0.78:.1f} {w*0.4:.1f}-{h:.1f} {w*0.75:.1f} {h*0.22:.1f} {w*1.15:.1f} {h*0.62:.1f} {w*0.4:.1f} {h:.1f}z" fill="#cdd3f3" stroke="{L}" stroke-width="2.2"/>')
    line(x + w * 0.4, 270, x + w * 0.4, 262, 2.2)


a('<defs>'
  '<linearGradient id="cyl" x1="0" x2="1"><stop offset="0" stop-color="#f3f5fd"/><stop offset=".55" stop-color="#e6e9f9"/><stop offset="1" stop-color="#cfd5f2"/></linearGradient>'
  '<linearGradient id="col" x1="0" x2="1"><stop offset="0" stop-color="#d6dbf4"/><stop offset=".45" stop-color="#eef0fb"/><stop offset="1" stop-color="#d0d6f2"/></linearGradient>'
  '<linearGradient id="dome" x1="0" x2="1"><stop offset="0" stop-color="#f1f3fc"/><stop offset=".6" stop-color="#e3e7f8"/><stop offset="1" stop-color="#c9d0f0"/></linearGradient>'
  '</defs>')

# ---------------------------------------------------------------- Leaning Tower of Pisa (x 46-134)
shadow(92, 110)
a('<g transform="rotate(4.2 90 270)">')
X0, X1 = 50, 130
a(f'<rect x="{X0}" y="62" width="{X1-X0}" height="208" fill="url(#cyl)" stroke="{L}" stroke-width="2.4"/>')
# base: blind arcade, tall
for i in range(5):
    arch(X0 + 5 + i * 14.6, 266, 9.5, 30, F2, 1.5)
levels = [(236, 202), (202, 168), (168, 134), (134, 100), (100, 66)]
line(X0 - 3, 236, X1 + 3, 236, 2.4); line(X0 - 3, 239, X1 + 3, 239, 1.4)
for top_base, top in levels:
    # cornice
    line(X0 - 3, top, X1 + 3, top, 2.4); line(X0 - 3, top + 3, X1 + 3, top + 3, 1.4)
    # loggia: 6 arches with slim columns
    for i in range(6):
        arch(X0 + 3.5 + i * 12.4, top_base - 2, 8.6, 24, W, 1.4)
# belfry
a(f'<rect x="58" y="34" width="64" height="30" fill="url(#cyl)" stroke="{L}" stroke-width="2.4"/>')
for i in range(4):
    arch(62.5 + i * 14.6, 60, 9.5, 20, W, 1.4)
line(55, 34, 125, 34, 2.4); line(56, 31, 124, 31, 1.4)
a(f'<path d="M66 31v-5h48v5" fill="{F}" stroke="{L}" stroke-width="2"/>')
a('</g>')
cypress(152, 82)

# ---------------------------------------------------------------- Florence: Duomo (x 196-356) + campanile (x 382-414)
shadow(276, 180)
rect(198, 202, 156, 68, F)
for x in range(206, 352, 18):                       # marble panel pilasters
    line(x, 206, x, 268, 1.2, "#7c86c9")
line(198, 214, 354, 214, 1.4)
for x in (214, 250, 304, 336):
    arch(x - 5, 262, 11, 30, W, 1.5)
a(f'<circle cx="277" cy="236" r="10" fill="{W}" stroke="{L}" stroke-width="1.8"/>')
a(f'<circle cx="277" cy="236" r="4" fill="none" stroke="{L}" stroke-width="1.2"/>')
a(f'<path d="M192 202h168l-10-12H202z" fill="{F2}" stroke="{L}" stroke-width="2.2"/>')
# octagonal drum with oculi
rect(228, 160, 98, 30, F)
for x in (240, 260, 277, 294, 314):
    a(f'<circle cx="{x}" cy="175" r="5.5" fill="{W}" stroke="{L}" stroke-width="1.4"/>')
line(224, 160, 330, 160, 2.4)
# ribbed ogival dome
a(f'<path d="M230 158C230 116 252 90 277 74C302 90 324 116 324 158z" fill="url(#dome)" stroke="{L}" stroke-width="2.4"/>')
a(f'<path d="M253 158C254 124 264 98 277 76M301 158C300 124 290 98 277 76" fill="none" stroke="{L}" stroke-width="1.5"/>')
a(f'<path d="M233 140H321M237 122H317" fill="none" stroke="#9aa3dc" stroke-width="1"/>')
# lantern
a(f'<path d="M269 74V60h16v14z" fill="{F}" stroke="{L}" stroke-width="2"/>')
a(f'<path d="M267 60h20l-10-14z" fill="{F2}" stroke="{L}" stroke-width="2"/>')
a(f'<circle cx="277" cy="43" r="3" fill="{L}"/>')
# Giotto's campanile (stands apart)
shadow(398, 50)
rect(382, 64, 32, 206, F)
for y in (110, 150, 188, 226):
    line(380, y, 416, y, 1.8)
for x in (382, 414):
    pass
line(387, 66, 387, 268, 1, "#7c86c9"); line(409, 66, 409, 268, 1, "#7c86c9")
gothic(392, 104, 12, 30)
gothic(390, 146, 7, 26); gothic(399, 146, 7, 26)
gothic(390, 184, 7, 24); gothic(399, 184, 7, 24)
rect(394, 236, 8, 18, W, 1.4)
a(f'<path d="M377 64h42v-8h-42z" fill="{F2}" stroke="{L}" stroke-width="2.2"/>')
cypress(436, 70)

# ---------------------------------------------------------------- Colosseum (x 470-690)
shadow(580, 240)
a(f'<path d="M470 270V122C540 112 620 112 690 118V190H678V232H664V270z" fill="url(#col)" stroke="{L}" stroke-width="2.4"/>')
# attic (left part only, broken on the right)
for x in range(484, 640, 22):
    rect(x, 128, 9, 10, W, 1.4)
line(470, 146, 690, 148, 2.2)
line(470, 190, 690, 190, 2.2)
line(470, 232, 678, 232, 2.2)
for i in range(8):
    arch(475 + i * 26, 186, 15, 32, W, 1.6)
for i in range(7):
    arch(475 + i * 28, 229, 15, 34, W, 1.6)
for i in range(7):
    arch(475 + i * 26.4, 268, 15, 32, W, 1.6)
for x in range(470, 660, 26):                       # engaged columns
    line(x + 23, 150, x + 23, 186, 1, "#7c86c9")
cypress(712, 64)

# ---------------------------------------------------------------- St Peter's Basilica (x 756-936)
shadow(846, 200)
rect(758, 206, 176, 64, F)
for x in range(766, 932, 16):
    line(x, 214, x, 268, 1.8)
a(f'<path d="M752 206h188l-6-10H758z" fill="{F2}" stroke="{L}" stroke-width="2.2"/>')
a(f'<path d="M816 196L846 178L876 196z" fill="{F}" stroke="{L}" stroke-width="2.2"/>')
arch(838, 268, 16, 30, W, 1.8)
# drum with paired columns
rect(800, 156, 92, 34, F)
for x in range(806, 890, 12):
    line(x, 158, x, 188, 1.3)
for x in (812, 836, 860, 878):
    arch(x - 4, 184, 8, 16, W, 1.2)
line(796, 156, 896, 156, 2.4)
# ribbed dome
a(f'<path d="M802 154C802 114 822 92 846 88C870 92 890 114 890 154z" fill="url(#dome)" stroke="{L}" stroke-width="2.4"/>')
a(f'<path d="M824 154C825 122 834 100 846 89M868 154C867 122 858 100 846 89" fill="none" stroke="{L}" stroke-width="1.4"/>')
# lantern + cross
a(f'<path d="M839 88V74h14v14z" fill="{F}" stroke="{L}" stroke-width="2"/>')
a(f'<path d="M837 74h18l-9-10z" fill="{F2}" stroke="{L}" stroke-width="2"/>')
line(846, 64, 846, 50, 2.2); line(840, 56, 852, 56, 2.2)
cypress(958, 72)
cypress(1000, 54, 14)

# ---------------------------------------------------------------- ground
line(0, 270, 1080, 270, 3)
a('<rect x="0" y="271" width="1080" height="2" fill="#1a5fe0"/>')

svg = '<svg id="sky" class="abs" viewBox="0 0 1080 272" stroke-linejoin="round" stroke-linecap="round">' + "".join(out) + "</svg>"
s = open("bergamo_post.html").read()
i = s.index('  <svg id="sky"'); j = s.index("</svg>", s.index('<rect x="0" y="271"')) + 6
s = s[:i] + "  " + svg + s[j:]
s = s.replace('d="M520 1196 C 560 1120, 640 1060, 740 1010 S 930 900, 975 800 S 995 740, 990 715"',
              'd="M600 1196 C 640 1120, 690 1070, 728 1040 S 930 900, 975 800 S 995 740, 990 715"')
open("bergamo_post.html", "w").write(s)
print("skyline written")
