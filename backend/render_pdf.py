from __future__ import annotations

import base64

import markdown as markdown_lib
from weasyprint import HTML

LETTER_CSS = """
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

/* Letterhead spacing follows DIN 5008: roughly one blank line between the sender block and
   the address field, and two blank lines before and after the Betreffzeile. One blank line
   at this font size is ~15pt (10.5pt * 1.4 line-height). */
.letter-sender { margin: 0 0 22pt; }
.letter-recipient { margin: 0 0 15pt; }
.letter-date { text-align: right; margin: 0 0 29pt; }
.letter-subject { font-weight: 700; margin: 0 0 29pt; }
"""

CV_CSS = """
@page { size: A4; margin: 1.6cm 1.8cm; }
body {
  font-family: "Liberation Sans", Arial, Helvetica, sans-serif;
  font-size: 10pt;
  line-height: 1.45;
  color: #374151;
  background: #ffffff;
}
.cv-photo {
  float: right;
  width: 3.5cm;
  height: auto;
  margin: 0 0 8pt 14pt;
}
h1 {
  font-size: 21pt;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #111111;
  /* 6pt, not less: below ~4pt PDF text extraction stops emitting a line break here
     and ATS parsers read the name and the headline as one glued token. */
  margin: 0 0 6pt;
}
h1 + p { color: #6b7280; font-size: 9pt; margin: 0 0 10pt; }
h2 {
  font-size: 11pt;
  font-weight: 600;
  color: #111111;
  margin: 14pt 0 5pt;
}
/* The section rule comes from the Markdown "---" alone. Without clear it runs across the
   floated photo; a border on the first h2 on top of it drew a second line under the first.
   Clearance lands the rule flush against the photo and ignores the photo's own bottom
   margin, so the gap has to come from the rule that sits next to it. */
hr { clear: both; }
hr:first-of-type { margin-top: 14pt; }
h2:first-of-type {
  clear: both;
  padding-top: 11pt;
  margin-top: 4pt;
}
h3 { font-size: 10pt; font-weight: 600; color: #111111; margin: 8pt 0 1pt; }
p { margin: 0 0 6pt; }
ul { margin: 3pt 0 6pt 16pt; padding: 0; }
li { margin: 0 0 2pt; }
a { color: #111111; text-decoration: none; }
strong { font-weight: 600; color: #111111; }
"""

HTML_DOCUMENT = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<style>{css}</style></head><body>{body}</body></html>"
)


def render_markdown_to_pdf(
    markdown_text: str,
    *,
    css: str = LETTER_CSS,
    photo: bytes | None = None,
    include_photo: bool = True,
    line_breaks: bool = False,
) -> bytes:
    # The CV header and the skills block put each entry on its own line; without nl2br
    # Markdown folds them into one run-on paragraph and the separators disappear.
    extensions = ["extra", "nl2br"] if line_breaks else ["extra"]
    body_html = markdown_lib.markdown(markdown_text, extensions=extensions)
    if photo is not None and include_photo:
        body_html = f'<img class="cv-photo" src="{_image_data_uri(photo)}" alt="">' + body_html
    document_html = HTML_DOCUMENT.format(css=css, body=body_html)
    return HTML(string=document_html).write_pdf()


def _image_data_uri(photo: bytes) -> str:
    mime = "image/png" if photo[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    encoded = base64.b64encode(photo).decode("ascii")
    return f"data:{mime};base64,{encoded}"
