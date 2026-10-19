"""Render docs/twinning-vs-mms.md to docs/twinning-vs-mms.pdf (headless Chrome).

Relative links are rewritten to GitHub URLs so they work in the PDF.
Usage: python3 scripts/build_preprint_pdf.py
"""

import re
import subprocess
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "twinning-vs-mms.md"
OUT = ROOT / "docs" / "twinning-vs-mms.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BLOB = "https://github.com/MaxSemenchuk/hromada-strategy-collab/blob/main"

CSS = """
@page { size: A4; margin: 22mm 20mm; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 11pt; line-height: 1.4; color: #111; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 8pt; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; } h3 { font-size: 11.5pt; margin: 11pt 0 4pt; }
p { margin: 0 0 7pt; text-align: justify; } a { color: #1a4f8b; text-decoration: none; }
table { border-collapse: collapse; margin: 8pt 0 10pt; width: 100%; font-size: 9.5pt; page-break-inside: avoid; }
th, td { border-top: 1px solid #333; border-bottom: 1px solid #ccc; padding: 3pt 5pt; text-align: left; }
th { border-bottom: 1px solid #333; } code { font-family: Menlo, monospace; font-size: 9pt; }
ol, ul { margin: 0 0 7pt; padding-left: 18pt; } li { margin-bottom: 3pt; }
"""


def absolutize(md: str) -> str:
    def fix(m):
        text, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|#|mailto:)", url):
            return m.group(0)
        path = (SRC.parent / url).resolve().relative_to(ROOT)
        return f"[{text}]({BLOB}/{path})"
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", fix, md)


def main():
    html = markdown.markdown(absolutize(SRC.read_text(encoding="utf-8")), extensions=["tables"])
    doc = f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Two Networks of Cooperation</title><style>{CSS}</style><body>{html}</body></html>'
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "paper.html"
        f.write_text(doc, encoding="utf-8")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={OUT}", f.as_uri()], check=True, capture_output=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
