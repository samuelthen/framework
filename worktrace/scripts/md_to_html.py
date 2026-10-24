"""Render RESULTS.md to a single self-contained RESULTS.html (images embedded as base64)."""
import base64, os, re, sys
import markdown

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/RESULTS.md"
out = os.path.splitext(src)[0] + ".html"
base = os.path.dirname(src)
body = markdown.markdown(open(src).read(), extensions=["tables", "fenced_code"])


def embed(m):
    path = os.path.join(base, m.group(1))
    if not os.path.exists(path):
        return m.group(0)
    return 'src="data:image/png;base64,' + base64.b64encode(open(path, "rb").read()).decode() + '"'


body = re.sub(r'src="([^"]+\.png)"', embed, body)
title = re.search(r"<h1>(.*?)</h1>", body)
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WorkTrace Pilot Results</title><style>
:root{{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--code:#f2f1ee}}
body{{background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;max-width:1100px;margin:0 auto;padding:16px 24px 48px}}
h1{{font-size:24px}} h2{{font-size:19px;margin-top:36px;border-bottom:1px solid var(--line);padding-bottom:4px}} h3{{font-size:16px;margin-top:28px}}
p,li{{color:var(--ink)}} code{{background:var(--code);padding:1px 4px;border-radius:3px;font-size:13px}}
table{{border-collapse:collapse;font-size:14px;margin:12px 0;display:block;overflow-x:auto}}
th,td{{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}} th{{background:var(--code)}}
img{{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;margin:8px 0}}
</style></head><body>
{body}
</body></html>"""
open(out, "w").write(html)
print(out, len(html) // 1024, "KB")
