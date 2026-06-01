import io

import pypdf

from backend.render_pdf import render_markdown_to_pdf

CV_MARKDOWN = """# Ivan Petrov

## Summary
Senior Backend Engineer with experience in Python and FastAPI.

## Skills
Python, FastAPI, PostgreSQL, Docker
"""


def test_render_markdown_to_pdf_starts_with_pdf_header():
    pdf_bytes = render_markdown_to_pdf("# Hello\n\nWorld")

    assert pdf_bytes.startswith(b"%PDF")


def test_rendered_pdf_contains_selectable_text():
    pdf_bytes = render_markdown_to_pdf(CV_MARKDOWN)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted = "\n".join(page.extract_text() for page in reader.pages)

    assert "Senior Backend Engineer" in extracted
    assert "FastAPI" in extracted
