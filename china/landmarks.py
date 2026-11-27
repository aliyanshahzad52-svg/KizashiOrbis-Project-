"""Line illustration of Chinese landmarks (soft navy line + lavender fill, same family as the Italy reel).
Writes landmarks.svg (viewBox 0 0 1080 260, ground y=258). Temple of Heaven, pagoda, Great Wall with watchtowers,
Chinese gate (pailou), separated by space and small pine trees."""
L, F, F2, W, RED = "#2a3160", "#eef0fb", "#dfe3f6", "#f8f9fe", "#f0a39a"
o = []
a = o.append


def line(x1, y1, x2, y2, sw=1.6, c=L):
    a(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{c}" stroke-width="{sw}" fill="none"/>')


def roof(cx, y, w, h, fill=F2, sw=2.2):
    """Curved Chinese roof with upturned eaves; y = eave line."""
    hw = w / 2
    a(f'<path d="M{cx-hw-10:.1f} {y-6:.1f}Q{cx-hw:.1f} {y+2:.1f} {cx-hw+14:.1f} {y:.1f}H{cx+hw-14:.1f}Q{cx+hw:.1f} {y+2:.1f} {cx+hw+10:.1f} {y-6:.1f}'
      f'Q{cx+hw*0.55:.1f} {y-h*0.55:.1f} {cx:.1f} {y-h:.1f}Q{cx-hw*0.55:.1f} {y-h*0.55:.1f} {cx-hw-10:.1f} {y-6:.1f}z" fill="{fill}" stroke="{L}" stroke-width="{sw}"/>')


def pine(x, h):
    for k, (w, y) in enumerate(((26, 0), (20, 14), (13, 27))):
        a(f'<path d="M{x-w:.1f} {258-h*0.25-y:.1f}L{x:.1f} {258-h-y*0.2:.1f}L{x+w:.1f} {258-h*0.25-y:.1f}z" fill="#d3d9f3" stroke="{L}" stroke-width="1.8"/>')
    line(x, 258, x, 258 - h * 0.25, 2.2)


def shadow(cx, w):
    a(f'<ellipse cx="{cx}" cy="258" rx="{w/2}" ry="4" fill="#cdd3f0" opacity=".55"/>')


# --- Great Wall (left): wall ribbon over hills with two watchtowers
a(f'<path d="M0 230C60 214 110 200 160 206S250 226 300 214" fill="none" stroke="{L}" stroke-width="2"/>')
a(f'<path d="M0 246C60 230 110 216 160 222S250 242 300 230V258H0z" fill="{F}" stroke="{L}" stroke-width="2"/>')
for x in range(6, 296, 12):                      # battlements along the wall top
    yy = 230 - 16 * (1 - ((x - 160) / 160) ** 2) if x < 300 else 230
    a(f'<rect x="{x}" y="{yy - 8:.1f}" width="6" height="7" fill="{F}" stroke="{L}" stroke-width="1.3"/>')
for cx, top in ((70, 170), (232, 176)):
    shadow(cx, 60)
    a(f'<rect x="{cx-22}" y="{top}" width="44" height="{258-top}" fill="{F}" stroke="{L}" stroke-width="2.2"/>')
    for k in range(4):
        a(f'<rect x="{cx-21+k*12}" y="{top-8}" width="7" height="8" fill="{F}" stroke="{L}" stroke-width="1.4"/>')
    a(f'<path d="M{cx-7} {top+44}v-12a7 7 0 0 1 14 0v12z" fill="{W}" stroke="{L}" stroke-width="1.5"/>')

pine(330, 56)

# --- Temple of Heaven (centre-left): three round tiers on a marble terrace
cx = 450
shadow(cx, 200)
a(f'<path d="M{cx-100} 258v-12h200v12zM{cx-86} 246v-10h172v10z" fill="{F}" stroke="{L}" stroke-width="2"/>')
a(f'<rect x="{cx-58}" y="196" width="116" height="40" fill="{F}" stroke="{L}" stroke-width="2.2"/>')
for x in range(cx - 52, cx + 56, 13):
    line(x, 198, x, 234, 1.4, RED)
roof(cx, 196, 140, 30)
a(f'<rect x="{cx-44}" y="150" width="88" height="22" fill="{F}" stroke="{L}" stroke-width="2"/>')
for x in range(cx - 40, cx + 44, 11):
    line(x, 152, x, 170, 1.3, RED)
roof(cx, 150, 110, 28)
a(f'<rect x="{cx-30}" y="108" width="60" height="18" fill="{F}" stroke="{L}" stroke-width="2"/>')
roof(cx, 108, 80, 30)
a(f'<path d="M{cx} 78v-12" stroke="{L}" stroke-width="2.2"/><circle cx="{cx}" cy="62" r="5" fill="#f3cf7a" stroke="{L}" stroke-width="1.6"/>')

pine(586, 50)

# --- Pagoda (centre-right): five storeys
cx = 690
shadow(cx, 110)
a(f'<rect x="{cx-40}" y="236" width="80" height="22" fill="{F}" stroke="{L}" stroke-width="2"/>')
y, w = 236, 92
for k in range(5):
    h_st = 26 - k * 2
    roof(cx, y, w + 18, 14, F2, 2)
    a(f'<rect x="{cx-w/2+10:.1f}" y="{y-h_st-14:.1f}" width="{w-20:.1f}" height="{h_st:.1f}" fill="{F}" stroke="{L}" stroke-width="2"/>')
    a(f'<path d="M{cx-6} {y-14:.1f}v-{h_st-8:.1f}a6 6 0 0 1 12 0v{h_st-8:.1f}z" fill="{W}" stroke="{L}" stroke-width="1.3"/>')
    y -= h_st + 14
    w -= 12
roof(cx, y, w + 18, 14, F2, 2)
a(f'<path d="M{cx} {y-14}v-26" stroke="{L}" stroke-width="2.2"/>')
for k in range(3):
    a(f'<circle cx="{cx}" cy="{y-20-k*7}" r="{3.6-k*0.7:.1f}" fill="#f3cf7a" stroke="{L}" stroke-width="1.2"/>')

pine(790, 54)

# --- Pailou gate (right)
cx = 930
shadow(cx, 190)
for x in (cx - 80, cx - 30, cx + 22, cx + 72):
    a(f'<rect x="{x}" y="150" width="9" height="108" fill="{RED}" stroke="{L}" stroke-width="1.8"/>')
a(f'<rect x="{cx-88}" y="150" width="176" height="16" fill="{F}" stroke="{L}" stroke-width="2"/>')
a(f'<rect x="{cx-36}" y="118" width="72" height="20" fill="{F}" stroke="{L}" stroke-width="2"/>')
roof(cx, 150, 186, 22)
roof(cx, 118, 96, 22)
a(f'<rect x="{cx-18}" y="172" width="36" height="14" fill="#f3cf7a" stroke="{L}" stroke-width="1.4"/>')
pine(1050, 48)

line(0, 258, 1080, 258, 2.6)
svg = '<svg id="land" class="abs" viewBox="0 0 1080 260" stroke-linejoin="round" stroke-linecap="round">' + "".join(o) + "</svg>"
open("landmarks.svg", "w").write(svg)
print("wrote landmarks.svg")
