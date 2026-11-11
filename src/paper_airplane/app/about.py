"""Credit strings for the window. This module stays free of the display library."""

from __future__ import annotations

CAPTION = "Paper Airplane Flight Lab"

CREDIT = (
    "Developed by Sahand Ranjbaripour, Flight Dynamics course project "
    "under Prof. Amiri Atashgah, University of Tehran"
)

FOOTER = "Paper Airplane Flight Lab | S. Ranjbaripour"

HINT = "A opens About. Esc quits."

ABOUT_LINES: tuple[str, ...] = (
    "Paper Airplane Flight Lab",
    "Developed by Sahand Ranjbaripour",
    "GitHub: sahandrb",
    "Flight Dynamics course project under Prof. Amiri Atashgah",
    "University of Tehran",
    "Flight model: Robert F. Stengel, Flight Dynamics (2005),",
    "Example 1.3-1.",
    "Prof. Amiri Atashgah is the course supervisor, not a",
    "co-author of this software.",
)

ABOUT_TEXT = "\n".join(ABOUT_LINES)
