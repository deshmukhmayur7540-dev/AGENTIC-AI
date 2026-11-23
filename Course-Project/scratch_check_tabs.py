import re
with open("app/static/index.html", "r", encoding="utf-8") as f:
    text = f.read()

for m in re.finditer(r'<button[^>]*id=["\']tab-btn-[^"\']+["\'][^>]*>', text):
    print(m.group(0))
