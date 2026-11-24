"""Assemble ielts_reel.html from its template and the shared OrbisNexa end card of uk_reel.html."""
import re

u = open("uk_reel.html").read()
t = open("ielts_reel.tpl.html").read()

end_css = u[u.index("  /* END */"):u.index("  #grain {")]
end_html = u[u.index("  <!-- END -->"):u.index("  <canvas id=\"grain\"")]
svg_line = [l for l in u.split("\n") if l.startswith("const SVG = {")][0]
split_fn = u[u.index("function split(el) {"):u.index("// logo as 5 vertical strips")]
logo_fn = u[u.index("// logo as 5 vertical strips"):u.index("const tl = gsap.timeline")]
end_tl = u[u.index("  // ---- END 6.9 - 13.8"):u.index("}\n\n// film grain")]
end_tl = re.sub(r", (\d+\.\d+)\);", lambda m: f", {float(m.group(1)) + 6.2:.2f});", end_tl)
end_tl = end_tl.replace("show('#end', 6.9);", "show('#end', 12.89);").replace("6.9 - 13.8", "12.9 - 19.0")


def bands():
    return ('<div class="abs band b1"></div><div class="abs band b2"></div><div class="abs band b3"></div>'
            '<div class="abs band b4"></div><div class="abs edge"></div>')


def lines(*ls):
    return "".join(f'<div class="ln {s}{" acc" if acc else ""}"><span>{txt}</span></div>' for txt, s, acc in ls)


SC = [
    ("sc1", "ielts_book", [("IELTS", "L", 0), ("BENEFITS", "M", 1)]),
    ("sc2", "ielts_grad", [("IELTS", "L", 0), ("IS KEY TO", "M", 0), ("TOP UNIVERSITIES", "S", 1)]),
    ("sc3", "ielts_tablet", [("BOOST YOUR", "S", 0), ("CAREER", "L", 0), ("BOOST YOUR", "S", 0), ("SCORE", "L", 1)]),
    ("sc4", "ielts_meeting", [("OPEN DOORS", "S", 0), ("TO NEW", "L", 0), ("OPPORTUNITIES", "S", 1)]),
]
TOPS = {"sc1": 1440, "sc2": 1330, "sc3": 1230, "sc4": 1390}
scenes = "\n".join(
    f'  <div id="{i}" class="abs full scene"><img class="bg" src="bg/{img}.jpg">{bands()}'
    f'<div class="abs txt" style="top:{TOPS[i]}px">{lines(*ls)}</div></div>' for i, img, ls in SC)

out = (t.replace("{{END_CSS}}", end_css).replace("{{END_HTML}}", end_html).replace("{{SVG_LINE}}", svg_line)
        .replace("{{SPLIT_FN}}", split_fn).replace("{{LOGO_FN}}", logo_fn).replace("{{END_TL}}", end_tl)
        .replace("{{SCENES}}", scenes))
open("ielts_reel.html", "w").write(out)
print("wrote ielts_reel.html")
