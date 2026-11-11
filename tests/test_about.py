"""About-panel copy. These tests do not open a window."""

from paper_airplane.app.about import ABOUT_TEXT, CREDIT, FOOTER

EXPECTED_ABOUT = """\
Paper Airplane Flight Lab
Developed by Sahand Ranjbaripour
GitHub: sahandrb
Flight Dynamics course project under Prof. Amiri Atashgah
University of Tehran
Flight model: Robert F. Stengel, Flight Dynamics (2005),
Example 1.3-1.
Prof. Amiri Atashgah is the course supervisor, not a
co-author of this software."""


def test_about_text_matches_the_specification() -> None:
    assert ABOUT_TEXT == EXPECTED_ABOUT


def test_about_names_no_faculty() -> None:
    lowered = ABOUT_TEXT.lower()
    assert "faculty" not in lowered
    assert "department" not in lowered
    assert "Prof. Amiri Atashgah" in ABOUT_TEXT
    assert "not a" in ABOUT_TEXT
    assert "co-author" in ABOUT_TEXT
    assert "sahandrb" in lowered
    assert "university of tehran" in lowered


def test_splash_credit_and_footer() -> None:
    assert CREDIT == (
        "Developed by Sahand Ranjbaripour, Flight Dynamics course project "
        "under Prof. Amiri Atashgah, University of Tehran"
    )
    assert FOOTER == "Paper Airplane Flight Lab | S. Ranjbaripour"
