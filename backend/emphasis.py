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
#
# Both disciplines keep the master CV's groups; only their order differs, so how a label is
# written lives here. The bold form is not decoration — the grounding check strips exactly it before
# reading the skills behind it, which is what keeps a category name from counting as a claim.
_CV_RULES = _SHARED_RULES + (
    "\n- Reordering the skills is not licence to expand them. The section may only name terms the "
    "master CV names as skills; never coin a new skill label out of an experience bullet."
    "\n- Open each group's line with the master CV's own label in bold, word for word and in the "
    "master CV's language, as `**Label:**`, with that group's skills following on the same line. "
    "Never rename, merge or split a group. Only label a group that "
    "has skills to hold: an empty category is an invitation to fill it, and nothing in the skills "
    "section may be filled."
)

_CV_INSTRUCTIONS = {
    "design": (
        "This posting hires for design, so the CV has to read design-first.\n"
        "- In the skills section, put the master CV's design groups first — UI/UX design, usability "
        "and accessibility, analysis — then the implementation and AI groups, then methods. A "
        "stack taking up more of the page than the design work reads as a candidate applying for "
        "a different job.\n"
        "- The Weiterbildung is named in passing — a completed qualification that puts the "
        "candidate on both sides of the handover, design and implementation. The entry itself "
        "stays; only its technology enumeration shrinks, to the technologies this posting "
        "actually touches. This is the one list a design posting may shorten, and it overrides "
        "the rule about keeping a training's named technologies intact.\n"
        "- Within a role, put the design bullets before the development ones. The roles themselves "
        "keep the order the master CV gives them — reverse-chronological order is not something "
        "relevance may reshuffle.\n" + _CV_RULES
    ),
    "engineering": (
        "This posting hires for engineering, so the CV has to read development-first.\n"
        "- In the skills section, list the programming languages, frameworks and development tools "
        "first, then the AI tooling, then the design skills.\n"
        "- Order the master CV's skill groups like this: frontend, backend and APIs, "
        "infrastructure and tools, AI-assisted development, design and UX, methods. A reader "
        "screening for a developer finds the stack by category, not by scanning a flat list.\n"
        "- Within a role, put the development and technical bullets before the design ones. The "
        "roles themselves keep the order the master CV gives them — reverse-chronological order is "
        "not something relevance may reshuffle.\n"
        "- A role from the design track keeps at most three bullets: the ones naming technologies, "
        "implementation, or handover to developers. Bullets about team leadership, design process, "
        "branding, and print production are not carried over — they answer a question this posting "
        "does not ask. This narrows what a design role shows, not whether it is shown: the role "
        "stays, with its title and its dates.\n"
        "- A design-track role that ran longer than three years keeps up to five bullets instead of "
        "three. The longest engagement in the candidate's history cannot be the thinnest entry on "
        "the page: a reader who sees five years compressed below a three-month one stops reading "
        "for relevance and starts wondering what is being kept from them.\n"
        "- A design-track role that ended more than seven years before this posting keeps exactly "
        "one bullet.\n"
        "- Carrying a bullet over is selection, not editing. Take the master CV's sentence whole or "
        "leave it out. Never shorten one, never merge two into one, never write a summarising "
        "bullet of your own that stands for several.\n"
        "- Every position stays its own entry with its own heading and its own dates, exactly as "
        "the master CV writes them. Two positions are never combined into one entry, not even when "
        "both are down to a single bullet: a shared date range tells the reader neither of them "
        "truthfully.\n"
        "- A role that ran under a year keeps at most five bullets, whichever track it belongs to. "
        "This is a ceiling on the newest entry, not a demotion: it still comes first and it still "
        "carries the most. But a three-month engagement spelled out past five points, sitting above "
        "a five-year one, reads as padding rather than as relevance.\n"
        + _CV_RULES
    ),
}

_LETTER_INSTRUCTIONS = {
    "design": (
        "This posting hires for design, so the letter has to argue design first.\n"
        "- The requirements you connect to the candidate's experience are the design ones, and the "
        "first body paragraph is about design work.\n"
        "- The template's Weiterbildung paragraph collapses into a single sentence inside a design "
        "paragraph. What it establishes here is that the candidate knows both sides and has built "
        "the interfaces they designed — not what a training course covered.\n"
        "- Name at most four technologies in that sentence, the ones this posting actually asks "
        "for. The full stack belongs on an engineering application; in front of a design team it "
        "reads as a developer's letter sent to the wrong address. This overrides the rule about "
        "reproducing the training's technology list as it stands.\n"
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


# An AI posting hires a developer who builds on language models: the engineering emphasis.
_SAME_EMPHASIS_AS = {"ai": "engineering"}


def emphasis_instruction(discipline: str, *, kind: str) -> str:
    """The ordering instruction for one document, or "" when the posting fits neither track."""
    return _BY_KIND[kind].get(_SAME_EMPHASIS_AS.get(discipline, discipline), "")


def emphasis_section(discipline: str, *, kind: str) -> list[str]:
    """The instruction as prompt sections, ready to splice into a user message."""
    instruction = emphasis_instruction(discipline, kind=kind)
    return ["## Emphasis for this posting\n" + instruction] if instruction else []
