"""Fill the WhatsApp icon into the end-card template -> endcard.html."""
import re

wa = re.sub(r"<title>.*?</title>", "", open("assets/whatsapp.svg").read()).replace("`", "")
open("endcard.html", "w").write(open("endcard.tpl.html").read().replace("{{WA}}", wa))
print("wrote endcard.html")
