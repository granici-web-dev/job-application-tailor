"""What the application leads with, decided by the discipline the posting hires for.

The candidate has two tracks — a long design career and a newer development one. A posting
wants one of them in front. This turns the analysed discipline into an instruction that
reorders the documents without touching what they contain.
"""

from __future__ import annotations

_SHARED_RULES = (
    "- Emphasis is order and framing only. Nothing is dropped because it belongs to the other "
    "track: it moves down, it does not disappear.\n"
    "- Never restate a role's title to fit the emphasis. The titles in the experience section "
    "stay exactly as the master CV writes them."
)

# Putting a track first tempts the model to pad that track out. Reordering a list is not
# permission to grow it, and the skills section is where that shows up.
_CV_RULES = _SHARED_RULES + (
    "\n- Reordering the skills is not licence to expand them. The section may only name terms the "
    "master CV names as skills; never coin a new skill label out of an experience bullet."
)

_CV_INSTRUCTIONS = {
    "design": (
        "This posting hires for design, so the CV has to read design-first.\n"
        "- Open the summary with the design track record: UI/UX and product design, the years "
        "behind it, and the scope of it. Development and AI-supported work follow afterwards as "
        "supporting range, never as the lead.\n"
        "- In the skills section, list the design skills and design tools first, the programming "
        "skills after them, and the AI tooling last.\n"
        "- Within a role, put the design bullets before the development ones. The roles themselves "
        "keep the order the master CV gives them — reverse-chronological order is not something "
        "relevance may reshuffle.\n" + _CV_RULES
    ),
    "engineering": (
        "This posting hires for engineering, so the CV has to read development-first.\n"
        "- Open the summary with the frontend and fullstack development profile and the "
        "technologies behind it. The design background follows afterwards, as what makes the "
        "candidate's interface work stronger, never as the lead.\n"
        "- In the skills section, list the programming languages, frameworks and development tools "
        "first, then the AI tooling, then the design skills.\n"
        "- Within a role, put the development and technical bullets before the design ones. The "
        "roles themselves keep the order the master CV gives them — reverse-chronological order is "
        "not something relevance may reshuffle.\n" + _CV_RULES
    ),
}

_LETTER_INSTRUCTIONS = {
    "design": (
        "This posting hires for design, so the letter has to argue design first.\n"
        "- The requirements you connect to the candidate's experience are the design ones, and the "
        "first body paragraph is about design work.\n"
        "- The development and AI-supported work comes afterwards and briefly: the range that "
        "carries a design through to implementation. Never open with it.\n" + _SHARED_RULES
    ),
    "engineering": (
        "This posting hires for engineering, so the letter has to argue development first.\n"
        "- The requirements you connect to the candidate's experience are the technical ones, and "
        "the first body paragraph is about building software.\n"
        "- The design background comes afterwards and briefly: what makes the candidate's frontend "
        "work stronger. Never open with it.\n" + _SHARED_RULES
    ),
}

_BY_KIND = {"cv": _CV_INSTRUCTIONS, "cover_letter": _LETTER_INSTRUCTIONS}


def emphasis_instruction(discipline: str, *, kind: str) -> str:
    """The ordering instruction for one document, or "" when the posting fits neither track."""
    return _BY_KIND[kind].get(discipline, "")


def emphasis_section(discipline: str, *, kind: str) -> list[str]:
    """The instruction as prompt sections, ready to splice into a user message."""
    instruction = emphasis_instruction(discipline, kind=kind)
    return ["## Emphasis for this posting\n" + instruction] if instruction else []
