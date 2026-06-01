from __future__ import annotations

import markdown as markdown_lib
from weasyprint import HTML

ATS_CSS = """
@page { size: A4; margin: 2cm; }
body {
  font-family: "Liberation Sans", Arial, Helvetica, sans-serif;
  font-size: 10.5pt;
  line-height: 1.4;
  color: #000000;
  background: #ffffff;
}
h1 { font-size: 16pt; margin: 0 0 4pt; }
h2 { font-size: 12pt; margin: 12pt 0 4pt; border-bottom: 1px solid #000000; }
h3 { font-size: 11pt; margin: 8pt 0 2pt; }
p { margin: 0 0 6pt; }
ul { margin: 4pt 0 4pt 18pt; padding: 0; }
li { margin: 0 0 2pt; }
a { color: #000000; text-decoration: none; }
"""

HTML_DOCUMENT = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<style>{css}</style></head><body>{body}</body></html>"
)


def render_markdown_to_pdf(markdown_text: str) -> bytes:
    body_html = markdown_lib.markdown(markdown_text, extensions=["extra"])
    document_html = HTML_DOCUMENT.format(css=ATS_CSS, body=body_html)
    return HTML(string=document_html).write_pdf()
