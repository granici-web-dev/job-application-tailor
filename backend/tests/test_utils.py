from backend.utils import (
    cover_letter_filename,
    cv_filename,
    resolve_unique_company_dir,
    sanitize_path_component,
)


def test_sanitize_replaces_illegal_chars_and_spaces():
    assert sanitize_path_component('Acme / GmbH: "Tech"*?') == "Acme_GmbH_Tech"


def test_sanitize_collapses_and_trims_underscores():
    assert sanitize_path_component("  Foo   Bar  ") == "Foo_Bar"


def test_sanitize_falls_back_when_empty():
    assert sanitize_path_component("///") == "unknown"


def test_cv_filename_format():
    assert cv_filename("Ivan Petrov", "Acme GmbH") == "CV_Ivan_Petrov_Acme_GmbH.pdf"


def test_cover_letter_filename_format():
    assert cover_letter_filename("Ivan Petrov", "Acme GmbH") == "CoverLetter_Ivan_Petrov_Acme_GmbH.pdf"


def test_resolve_unique_company_dir_adds_numeric_suffix_on_collision(tmp_path):
    first = resolve_unique_company_dir(tmp_path, "Acme GmbH")
    assert first == tmp_path / "Acme_GmbH"
    first.mkdir()

    second = resolve_unique_company_dir(tmp_path, "Acme GmbH")
    assert second == tmp_path / "Acme_GmbH_2"
    second.mkdir()

    third = resolve_unique_company_dir(tmp_path, "Acme GmbH")
    assert third == tmp_path / "Acme_GmbH_3"
