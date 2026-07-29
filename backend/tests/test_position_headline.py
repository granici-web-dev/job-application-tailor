from backend.tailor_cv import apply_position_headline

TITLE = "Frontend Developer (m/w/d) – React & TypeScript"


def test_inserts_the_position_under_the_name():
    cv = "# Serghei Granici\n\nWacholderweg 6 · +49 172\n\n## Profil\n\nText.\n"

    result = apply_position_headline(cv, TITLE)

    assert result == (
        f"# Serghei Granici\n\n**{TITLE}**\n\nWacholderweg 6 · +49 172\n\n## Profil\n\nText.\n"
    )


def test_replaces_a_headline_the_model_wrote_itself():
    cv = "# Serghei Granici\n\n**UI/UX Designer**\n\nWacholderweg 6\n\n## Profil\n\nText.\n"

    result = apply_position_headline(cv, TITLE)

    assert f"# Serghei Granici\n\n**{TITLE}**\n\nWacholderweg 6" in result
    assert "UI/UX Designer" not in result


def test_keeps_the_rest_of_the_document_intact():
    cv = "# Serghei Granici\n\n**Alt**\n\n## Profil\n\nText.\n\n## Sprachen\n\n- Deutsch\n"

    result = apply_position_headline(cv, TITLE)

    assert result.endswith("## Profil\n\nText.\n\n## Sprachen\n\n- Deutsch\n")
    assert result.count("**") == 2


def test_leaves_the_cv_alone_when_there_is_no_name_heading():
    cv = "Serghei Granici\n\nWacholderweg 6\n\n## Profil\n\nText.\n"

    assert apply_position_headline(cv, TITLE) == cv


def test_does_not_mistake_a_section_heading_for_the_name():
    cv = "## Profil\n\n**Junior Developer**\n\nText.\n"

    assert apply_position_headline(cv, TITLE) == cv


def test_preserves_a_missing_trailing_newline():
    cv = "# Serghei Granici\n\nWacholderweg 6"

    assert apply_position_headline(cv, TITLE).endswith("Wacholderweg 6")
