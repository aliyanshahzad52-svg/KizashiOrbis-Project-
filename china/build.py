"""Assemble china.html from the template, the landmark SVG and plane windows."""
s = open("china.tpl.html").read()
win = "".join(f'<circle cx="{x}" cy="{44 - (x - 60) * 0.06:.1f}" r="3.2"/>' for x in range(60, 196, 13))
s = s.replace("{{LAND}}", open("landmarks.svg").read()).replace("{{WIN}}", win)
open("china.html", "w").write(s)
print("wrote china.html")
