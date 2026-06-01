import json
from pathlib import Path

import pytest

from backend.errors import ProfileError
from backend.profile import load_photo_bytes, load_profile

FIXTURE_PROFILE = Path(__file__).parent / "fixtures" / "profile"


def _write_profile(directory, *, personal=None, master_cv="# CV\n\nReal content here.", template="Dear team,"):
    if personal is not None:
        (directory / "personal.json").write_text(json.dumps(personal), encoding="utf-8")
    if master_cv is not None:
        (directory / "master_cv.md").write_text(master_cv, encoding="utf-8")
    if template is not None:
        (directory / "cover_letter_template.md").write_text(template, encoding="utf-8")


def test_load_profile_reads_all_three_files():
    profile = load_profile(FIXTURE_PROFILE)

    assert profile.personal.full_name == "Ivan Petrov"
    assert profile.personal.languages == ["Russian (native)", "German (B2)", "English (C1)"]
    assert "FastAPI" in profile.master_cv_markdown
    assert "Kind regards" in profile.cover_letter_template


def test_load_profile_raises_when_master_cv_missing(tmp_path):
    _write_profile(tmp_path, personal={"full_name": "A", "email": "a@b.c"}, master_cv=None)

    with pytest.raises(ProfileError, match="master_cv.md"):
        load_profile(tmp_path)


def test_load_profile_raises_on_invalid_personal_json(tmp_path):
    (tmp_path / "personal.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "master_cv.md").write_text("# CV", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Dear team,", encoding="utf-8")

    with pytest.raises(ProfileError, match="valid JSON"):
        load_profile(tmp_path)


def test_load_profile_requires_email(tmp_path):
    _write_profile(tmp_path, personal={"full_name": "Ivan Petrov"})

    with pytest.raises(ProfileError, match="email"):
        load_profile(tmp_path)


def test_load_profile_treats_missing_optional_fields_as_absent(tmp_path):
    _write_profile(tmp_path, personal={"full_name": "Ivan Petrov", "email": "ivan@example.com"})

    profile = load_profile(tmp_path)

    assert profile.personal.phone is None
    assert profile.personal.languages == []


def test_load_profile_defaults_photo_path():
    profile = load_profile(FIXTURE_PROFILE)

    assert profile.personal.photo_path == FIXTURE_PROFILE / "photo.jpg"


def test_load_profile_reads_explicit_photo_path(tmp_path):
    _write_profile(
        tmp_path,
        personal={"full_name": "Ivan", "email": "a@b.c", "photo": "assets/me.png"},
    )

    profile = load_profile(tmp_path)

    assert profile.personal.photo_path == Path("assets/me.png")


def test_load_photo_bytes_returns_none_when_missing(tmp_path):
    assert load_photo_bytes(tmp_path / "nope.jpg") is None
    assert load_photo_bytes(None) is None


def test_load_photo_bytes_reads_existing_file(tmp_path):
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xe0jpeg-bytes")

    assert load_photo_bytes(photo) == b"\xff\xd8\xff\xe0jpeg-bytes"
