import re
import json

with open("app/static/index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

with open("app/static/app.js", "r", encoding="utf-8") as f:
    js_content = f.read()

html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))
print(f"Total HTML IDs found: {len(html_ids)}")

js_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js_content))
print(f"Total JS getElementById IDs found: {len(js_ids)}")

missing_in_html = js_ids - html_ids
print(f"JS IDs missing in HTML ({len(missing_in_html)}):")
for mid in sorted(missing_in_html):
    print("  MISSING:", mid)

# Find all buttons in HTML and check if they have listeners or IDs in JS
html_buttons = re.findall(r'<button[^>]*id=["\']([^"\']+)["\'][^>]*>', html_content)
print(f"\nHTML Buttons with IDs ({len(html_buttons)}):")
for btn_id in html_buttons:
    has_listener = (btn_id in js_content) or (f"'{btn_id}'" in js_content) or (f'"{btn_id}"' in js_content)
    if not has_listener:
        print(f"  NO JS REFERENCE FOR BUTTON: {btn_id}")

# Find all api calls in JS
api_calls = set(re.findall(r"apiCall\(['\"]([^'\"]+)['\"]", js_content))
template_api_calls = set(re.findall(r"apiCall\(`([^`]+)`", js_content))
print(f"\nAPI calls in JS:")
for call in sorted(api_calls):
    print("  LITERAL:", call)
for call in sorted(template_api_calls):
    print("  TEMPLATE:", call)
