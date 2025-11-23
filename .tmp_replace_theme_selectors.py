from pathlib import Path

path = Path("core/static/core/css/style.css")
data = path.read_text()
needle = "body.theme-dark"
replacement = "body.theme-dark, body[data-theme=\"dark\"], html.theme-dark, html[data-theme=\"dark\"]"
if needle not in data:
    raise SystemExit("needle not found")
path.write_text(data.replace(needle, replacement))

