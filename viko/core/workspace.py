from __future__ import annotations
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


WORKSPACE = _base_dir() / "workspace"
_CATEGORIES = ("wireframes", "presentations", "documents", "code")


def ensure_dirs() -> None:
    for cat in _CATEGORIES:
        (WORKSPACE / cat).mkdir(parents=True, exist_ok=True)


def save_file(content: str, filename: str, category: str = "documents") -> Path:
    if category not in _CATEGORIES:
        category = "documents"
    ensure_dirs()
    path = WORKSPACE / category / filename
    path.write_text(content, encoding="utf-8")
    return path


def file_url(path: Path) -> str:
    return path.as_uri()


def list_files(category: str) -> list[dict]:
    ensure_dirs()
    folder = WORKSPACE / category
    result = []
    for f in sorted(folder.iterdir()):
        if f.name.startswith("."):
            continue
        result.append({
            "name": f.name,
            "path": str(f),
            "url":  file_url(f),
            "size": f.stat().st_size,
        })
    return result


def html_template(title: str, body_html: str, styles: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #000;
    color: #c8e8f8;
    font-family: 'Courier New', monospace;
    padding: 24px;
    min-height: 100vh;
  }}
  h1, h2, h3 {{ color: #00d4ff; margin-bottom: 12px; }}
  a {{ color: #00d4ff; }}
  hr {{ border-color: rgba(0,212,255,0.2); margin: 16px 0; }}
  {styles}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def wireframe_template(title: str, components: list[dict]) -> str:
    boxes = ""
    for c in components:
        x, y = c.get("x", 0), c.get("y", 0)
        w, h = c.get("w", 120), c.get("h", 40)
        lbl  = c.get("label", "")
        kind = c.get("type", "box")
        color_map = {
            "button": "rgba(0,212,255,0.25)",
            "input":  "rgba(255,179,71,0.15)",
            "image":  "rgba(80,80,80,0.4)",
            "text":   "transparent",
            "box":    "rgba(0,212,255,0.08)",
        }
        bg = color_map.get(kind, "rgba(0,212,255,0.08)")
        boxes += (
            f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
            f'border:1px solid rgba(0,212,255,0.5);background:{bg};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:11px;color:#c8e8f8;border-radius:3px;">'
            f'{lbl}</div>'
        )
    body = (
        f'<h2 style="margin-bottom:16px">{title}</h2>'
        f'<div style="position:relative;height:700px;border:1px solid rgba(0,212,255,0.2);'
        f'border-radius:4px;padding:8px;">{boxes}</div>'
    )
    return html_template(title, body)


def presentation_template(title: str, slides: list[dict]) -> str:
    slides_html = ""
    for slide in slides:
        notes = slide.get("notes", "")
        notes_html = f'<aside class="notes">{notes}</aside>' if notes else ""
        slides_html += f"""
        <section>
          <h2>{slide.get("title", "")}</h2>
          <div class="content">{slide.get("content", "")}</div>
          {notes_html}
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/black.css">
<style>
  .reveal {{ font-family: 'Courier New', monospace; }}
  .reveal h2 {{ color: #00d4ff; text-transform: none; }}
  .reveal .content {{ font-size: 0.85em; line-height: 1.6; }}
  .reveal section {{ text-align: left; padding: 0 40px; }}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">{slides_html}
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script>Reveal.initialize({{ hash: true, transition: 'fade' }});</script>
</body>
</html>"""
