from __future__ import annotations

import base64
import re
from dataclasses import dataclass

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
/* One value of the header — an address, an e-mail, a URL — never breaks inside; a line too
   long for the page breaks at the " · " between two of them. */
.header-item { white-space: nowrap; }
/* A section the page limit starts a new page with: `## Kenntnisse {: .new-page }`. */
.new-page { break-before: page; }
"""



@dataclass(frozen=True)
class CvLayout:
    """The knobs the page limit may turn on the CV layout, defaults as in CV_CSS."""

    compact_spacing: bool = False
    margin_vertical_mm: float = 16
    margin_horizontal_mm: float = 18
    font_pt: float = 10

    def describe(self) -> str:
        spacing = "compact" if self.compact_spacing else "normal"
        return (
            f"spacing {spacing}, margins {self.margin_vertical_mm:g} × "
            f"{self.margin_horizontal_mm:g} mm, body font {self.font_pt:g} pt"
        )


DEFAULT_CV_LAYOUT = CvLayout()

# Tighter gaps between sections, entries and bullets. Appended after CV_CSS, so each rule
# overrides the one with the same selector there; line height and font sizes stay as they are.
COMPACT_SPACING_CSS = """
h1 + p { margin: 0 0 6pt; }
h2 { margin: 8pt 0 3pt; }
h2:first-of-type { padding-top: 6pt; margin-top: 2pt; }
hr { margin: 6pt 0; }
hr:first-of-type { margin-top: 8pt; }
h3 { margin: 5pt 0 1pt; }
p { margin: 0 0 4pt; }
ul { margin: 2pt 0 3pt 16pt; }
li { margin: 0 0 1pt; }
"""


def cv_css(layout: CvLayout = DEFAULT_CV_LAYOUT) -> str:
    parts = [CV_CSS]
    if layout.compact_spacing:
        parts.append(COMPACT_SPACING_CSS)
    if (layout.margin_vertical_mm, layout.margin_horizontal_mm) != (
        DEFAULT_CV_LAYOUT.margin_vertical_mm,
        DEFAULT_CV_LAYOUT.margin_horizontal_mm,
    ):
        parts.append(
            f"@page {{ margin: {layout.margin_vertical_mm:g}mm {layout.margin_horizontal_mm:g}mm; }}"
        )
    if layout.font_pt != DEFAULT_CV_LAYOUT.font_pt:
        parts.append(f"body {{ font-size: {layout.font_pt:g}pt; }}")
    return "\n".join(parts)


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
    return render_markdown_with_page_count(
        markdown_text, css=css, photo=photo, include_photo=include_photo, line_breaks=line_breaks
    )[0]


def render_markdown_with_page_count(
    markdown_text: str,
    *,
    css: str = LETTER_CSS,
    photo: bytes | None = None,
    include_photo: bool = True,
    line_breaks: bool = False,
) -> tuple[bytes, int]:
    """The PDF and its page count, from one layout pass."""
    _, document = _laid_out(markdown_text, css, photo, include_photo, line_breaks)
    return document.write_pdf(), len(document.pages)


def section_page_spans(
    markdown_text: str,
    *,
    css: str = LETTER_CSS,
    photo: bytes | None = None,
    include_photo: bool = True,
    line_breaks: bool = False,
) -> list[tuple[int, int]]:
    """For each `## ` section in order, the first and last page (from 0) it is laid out on.

    A section runs from its heading to the next one. Its elements are found on the pages by
    identity, so nothing is wrapped around them and the layout is the one the PDF gets.
    """
    html, document = _laid_out(markdown_text, css, photo, include_photo, line_breaks)
    section_of: dict[object, int] = {}
    body = html.etree_element.find("body")
    section = -1
    for child in body if body is not None else []:
        if child.tag == "h2":
            section += 1
        if section >= 0:
            for element in child.iter():
                section_of[element] = section
    spans: dict[int, list[int]] = {}
    for number, page in enumerate(document.pages):
        for box in page._page_box.descendants():
            index = section_of.get(getattr(box, "element", None))
            if index is not None:
                spans.setdefault(index, [number, number])[1] = number
    return [tuple(spans[index]) for index in sorted(spans)]


def _laid_out(markdown_text: str, css: str, photo: bytes | None, include_photo: bool, line_breaks: bool):
    # The CV header and the skills block put each entry on its own line; without nl2br
    # Markdown folds them into one run-on paragraph and the separators disappear.
    extensions = ["extra", "nl2br"] if line_breaks else ["extra"]
    body_html = _unbroken_header_items(markdown_lib.markdown(markdown_text, extensions=extensions))
    if photo is not None and include_photo:
        body_html = f'<img class="cv-photo" src="{_image_data_uri(photo)}" alt="">' + body_html
    html = HTML(string=HTML_DOCUMENT.format(css=css, body=body_html))
    return html, html.render()


HEADER_SEPARATOR = " · "
HEADER_END = re.compile(r"<h2|<hr")
PARAGRAPH = re.compile(r"(<p>)(.*?)(</p>)", re.S)
LINE_BREAK = re.compile(r"(<br\s*/?>\s*)")


def _unbroken_header_items(body_html: str) -> str:
    """Each " · "-separated value of the CV header in its own unbreakable span.

    The header is what stands between the name heading and the first section; a document
    that does not open with a name heading (the letter) has none.
    """
    if not body_html.lstrip().startswith("<h1"):
        return body_html
    end = HEADER_END.search(body_html)
    cut = end.start() if end else len(body_html)
    header = PARAGRAPH.sub(lambda match: match.group(1) + _wrapped_lines(match.group(2)) + match.group(3), body_html[:cut])
    return header + body_html[cut:]


def _wrapped_lines(paragraph: str) -> str:
    parts = LINE_BREAK.split(paragraph)
    # The split keeps the <br> between lines at the odd indexes.
    return "".join(
        part if index % 2 else HEADER_SEPARATOR.join(
            f'<span class="header-item">{item}</span>' for item in part.split(HEADER_SEPARATOR)
        )
        for index, part in enumerate(parts)
    )


def _image_data_uri(photo: bytes) -> str:
    mime = "image/png" if photo[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    encoded = base64.b64encode(photo).decode("ascii")
    return f"data:{mime};base64,{encoded}"
