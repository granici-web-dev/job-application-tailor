import inspect
import io

import pypdf

from backend.render_pdf import CV_CSS, LETTER_CSS, render_markdown_to_pdf

CV_MARKDOWN = """# Ivan Petrov

ivan.petrov@example.com | +49 151 23456789 | Siegburg

## Profil
Senior Backend Engineer with Python and FastAPI.

## Kenntnisse
Python, FastAPI, PostgreSQL, Docker
"""

LETTER_MARKDOWN = """Dear Acme GmbH team,

I am writing about the Backend Engineer role and my work with Python services.

Kind regards,
Ivan Petrov
"""


def _images(pdf_bytes):
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return [image for page in reader.pages for image in page.images]


def _text(pdf_bytes):
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_render_cv_embeds_image_and_keeps_selectable_text(tiny_jpeg):
    pdf = render_markdown_to_pdf(CV_MARKDOWN, css=CV_CSS, photo=tiny_jpeg, include_photo=True)

    assert pdf.startswith(b"%PDF")
    assert len(_images(pdf)) >= 1
    text = _text(pdf)
    assert text.index("Ivan Petrov") < text.index("Profil") < text.index("Kenntnisse")


def test_render_cv_include_photo_false_has_no_image_text_intact(tiny_jpeg):
    pdf = render_markdown_to_pdf(CV_MARKDOWN, css=CV_CSS, photo=tiny_jpeg, include_photo=False)

    assert _images(pdf) == []
    assert "Ivan Petrov" in _text(pdf)


def test_render_cv_without_photo_bytes_has_no_image():
    pdf = render_markdown_to_pdf(CV_MARKDOWN, css=CV_CSS, photo=None)

    assert _images(pdf) == []
    assert "Kenntnisse" in _text(pdf)


def test_photo_does_not_change_extracted_text(tiny_jpeg):
    with_photo = render_markdown_to_pdf(CV_MARKDOWN, css=CV_CSS, photo=tiny_jpeg, include_photo=True)
    without_photo = render_markdown_to_pdf(CV_MARKDOWN, css=CV_CSS, photo=None)

    assert "".join(_text(with_photo).split()) == "".join(_text(without_photo).split())


def test_render_letter_unchanged_single_column_selectable_text():
    assert inspect.signature(render_markdown_to_pdf).parameters["css"].default is LETTER_CSS
    forbidden = ("column-count", "columns", "float", "position: absolute", "position:absolute")
    assert not any(token in LETTER_CSS for token in forbidden)

    pdf = render_markdown_to_pdf(LETTER_MARKDOWN)

    assert pdf.startswith(b"%PDF")
    assert _images(pdf) == []
    assert "Kind regards" in _text(pdf)
