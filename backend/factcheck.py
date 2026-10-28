"""Deterministic fact check of a finished CV or cover letter against the master CV.

The humanize guard compares a document only with its own previous version, so whatever the
tailoring step got wrong survives it untouched: a number nobody stated, a technology moved to
an employer that never used it, a side project told as if it were done at the day job. This
module reads the finished text against the master CV itself.

It checks three things:
- every number in the text is a number the master CV states;
- every technology or method the text names exists in the master CV, under the same
  position or project the text ties it to — and inside a position that the master CV splits
  into projects under bold subheadings, under the same one of those;
- a side project is never told in the same breath as an employer, and a claim of N years
  only covers what the master CV covers with the same N years.

What counts as a technology or method is read from the master CV's own skills section, plus
the posting's skills that the master CV does not back — those are the ones a model imports.
A posting term that occurs only inside the posting's job title or company name is a quote of
the posting, not an import: "Business Analyst" in "Ihre Ausschreibung als Business Analyst".
A posting term of two technologies ("Next.js / React") is held part by part: it is backed when
the master CV backs each part, and the parts it lacks are the ones looked for.

A cover letter's opening paragraph describes the posting and the company, so the posting's
terms in it are theirs, not the candidate's. Only a sentence of the opening that speaks of
the candidate — "arbeite ich bereits mit React", "mein Stack", "ist mir vertraut" — is held
to the master CV; "habe ich Ihre Ausschreibung gelesen" and "reizt mich" make no claim.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from backend.grounding import NON_WORD, _is_supported, _normalize, _skill_items

SECTION = re.compile(r"^##\s+(.*)$")
ENTRY = re.compile(r"^###\s+(.*)$")
# A line that is nothing but bold text heads a project inside a position.
UNIT_HEADING = re.compile(r"^\s*\*\*([^*]+?)\*\*\s*$")
EXPERIENCE_SECTION = re.compile(
    r"(berufserfahrung|beruflicher werdegang|werdegang|experience|employment)", re.IGNORECASE
)
PROJECT_SECTION = re.compile(r"(projekte|projects)", re.IGNORECASE)
SKILL_SECTION = re.compile(r"(kenntnis|f[äa]higkeit|skill|kompetenz|technical)", re.IGNORECASE)
PARENTHETICAL = re.compile(r"\([^)]*\)")
# Where a job title's core ends: "Frontend Developer (m/w/d) React / TypeScript".
TITLE_CORE_END = re.compile(r"\(|\s[–—|-]\s")

NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?!\w)")
DURATION = re.compile(r"(?<![\w.])(\d+)\+?\s*(?:jahre|jahren|years?)\b", re.IGNORECASE)
# Not at a colon: what follows one belongs to the claim before it ("10 Jahre …: WCAG").
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")

# Spelled-out numbers count as numbers: "sechs Rollen" claims the same thing as "6 Rollen".
# One is left out on purpose — "ein" and "one" are articles far more often than counts.
NUMBER_WORDS = {
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
    "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "zwanzig": 20,
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20,
}
_NUMBER_WORD = "|".join(NUMBER_WORDS)
SPELLED_YEARS = re.compile(rf"\b({_NUMBER_WORD}|\d+)-?jährig\w*", re.IGNORECASE)
SPELLED_NUMBER = re.compile(rf"\b({_NUMBER_WORD})\b", re.IGNORECASE)
# An adjective's ending, which two words share without sharing a head: "öffentliche" and
# "staatliche" end alike, yet one does not name the other.
ADJECTIVE_ENDING = re.compile(r"(lich|isch|ig|bar|sam|haft)(e|en|er|es|em)?$")

# Below this length a term ("UX", "UI", "Nx") is too generic to pin to one position: it
# turns up in nearly every entry under some other spelling.
MIN_TERM_LENGTH = 3
MAX_POSTING_TERM_WORDS = 4
# A posting term's parts: "Next.js / React", "Next.js/React".
TERM_PART_SEPARATOR = "/"

# The letter's paragraphs: the salutation first, then the opening about the posting.
INTRO_INDEX = 1
# What makes a sentence of the opening a claim about the candidate: a possessive on its own
# ("mein Stack"), the subject with a verb of doing or having ("arbeite ich bereits mit"), or
# the object with a predicate of acquaintance ("ist mir vertraut"). "habe ich Ihre
# Ausschreibung gelesen", "hat mein Interesse geweckt" and "reizt mich die Verbindung aus
# AdTech" claim nothing.
FIRST_PERSON_POSSESSIVE = re.compile(r"\b(?:mein\w*|my)\b", re.IGNORECASE)
POSSESSIVE_IDIOM = re.compile(
    r"\b(?:mein\w*|my)\s+(?:Interesse|Aufmerksamkeit|Bewerbung|Unterlagen|Lebenslauf|interest|"
    r"attention|application)\b",
    re.IGNORECASE,
)
FIRST_PERSON_SUBJECT = re.compile(r"(?i:\bich\b)|\bI\b")
FIRST_PERSON_OBJECT = re.compile(r"\b(?:mich|mir|me|myself)\b", re.IGNORECASE)
DOING_VERB = re.compile(
    r"\b(?:arbeite|arbeitete|gearbeitet|nutze|genutzt|verwende|verwendet|setze|eingesetzt|"
    r"entwickle|entwickelt|entwickelte|baue|gebaut|baute|bringe|mitbringe|einbringe|kenne|"
    r"beherrsche|betreue|verantworte|gestalte|gestaltet|umgesetzt|realisiert|implementiert|"
    r"programmiere|programmiert|beschäftige|beschäftigt|praktiziere|erfahrung|erfahren|"
    r"vertraut|geläufig|bereits|schon|"
    r"work|worked|working|use|used|using|build|built|develop|developed|experience|experienced|"
    r"familiar|already|know)\b",
    re.IGNORECASE,
)
ACQUAINTANCE = re.compile(r"\b(?:vertraut|geläufig|familiar)\b", re.IGNORECASE)


@dataclass(frozen=True)
class _Place:
    """Where a fact may live: a whole entry, or one project inside it."""

    name: str
    text: str


@dataclass(frozen=True)
class _Unit:
    name: str
    text: str
    anchors: frozenset[str]


@dataclass(frozen=True)
class _Entry:
    name: str
    kind: str  # "experience", "project" or "other"
    text: str
    # The entry's text outside its units: heading, dates, any line that speaks for all of them.
    common: str
    anchors: frozenset[str]
    units: tuple[_Unit, ...]

    def place(self) -> _Place:
        return _Place(self.name, self.text)

    def unit_place(self, unit: _Unit) -> _Place:
        return _Place(f"{self.name} › {unit.name}", self.common + "\n" + unit.text)


@dataclass(frozen=True)
class _Master:
    text: str
    entries: list[_Entry]
    terms: list[str]
    numbers: set[str]
    durations: dict[str, list[str]]


def check_cv(
    cv_markdown: str,
    master_markdown: str,
    *,
    posting_terms: list[str],
    allowed_text: str = "",
    posting_names: Sequence[str] = (),
) -> list[str]:
    """Every statement in the CV the master CV does not back, as human-readable findings.

    `allowed_text` holds data the CV may quote that is not in the master CV — the contact
    details, the posting's title and company — so their numbers are not reported.
    `posting_names` are the posting's job title and company name: a posting term inside one
    of them is not reported.
    """
    master = _read_master(master_markdown)
    findings = _Findings(master, posting_terms, allowed_text, posting_names)

    for section, lines in _sections(cv_markdown):
        if SKILL_SECTION.search(section):
            findings.numbers_only("\n".join(lines))
            continue
        intro, entries = _split_entries(lines)
        for sentence in _sentences("\n".join(intro)):
            findings.sentence(sentence, scope=None)
            findings.no_mixing(sentence, what="this sentence")
        for heading, body in entries:
            matched = _mentioned(heading, master.entries)
            if len(matched) != 1:
                findings.add(
                    f"The entry '{heading}' matches no position or project in the master CV."
                    if not matched
                    else f"The entry '{heading}' combines {_names(matched)} into one."
                )
                continue
            _check_cv_entry(findings, matched[0], body)
    return findings.result()


def _check_cv_entry(findings: _Findings, entry: _Entry, body: list[str]) -> None:
    current: list[_Unit] = []
    for line in body:
        if UNIT_HEADING.match(line):
            current = _mentioned_units(line, entry)
        for sentence in _sentences(line):
            units = _mentioned_units(sentence, entry) or current
            scope = [entry.unit_place(unit) for unit in units] or [entry.place()]
            findings.sentence(sentence, scope=scope)
            others = [other for other in _mentioned(sentence, findings.master.entries) if other != entry]
            if others:
                findings.add(
                    f"The entry '{entry.name}' mentions {_names(others)}, which the master CV "
                    "keeps separate."
                )


def check_letter(
    letter_markdown: str,
    master_markdown: str,
    *,
    posting_terms: list[str],
    allowed_text: str = "",
    posting_names: Sequence[str] = (),
) -> list[str]:
    """Every statement in the cover letter body the master CV does not back.

    A letter has no entry headings, so the position a sentence talks about is read from the
    names it mentions, and so is the project inside that position. A sentence that names
    neither continues the one before it in the same paragraph; the first sentence of a
    paragraph that names nothing is held to the master CV as a whole.

    The body starts with the salutation; the paragraph after it is the opening, which
    describes the posting and the company. Of the opening, only the sentences that speak of
    the candidate are checked (see `claims_about_candidate`).
    """
    master = _read_master(master_markdown)
    findings = _Findings(master, posting_terms, allowed_text, posting_names)

    paragraphs = [part for part in re.split(r"\n\s*\n", letter_markdown) if part.strip()]
    for index, paragraph in enumerate(paragraphs):
        sentences = _sentences(paragraph)
        if index == INTRO_INDEX:
            sentences = [sentence for sentence in sentences if claims_about_candidate(sentence)]
        else:
            findings.no_mixing(paragraph, what="one paragraph")
        entries: list[_Entry] = []
        units: dict[str, list[_Unit]] = {}
        for sentence in sentences:
            mentioned = _mentioned(sentence, master.entries)
            if mentioned:
                entries, units = mentioned, {}
            for entry in entries:
                named = _mentioned_units(sentence, entry)
                if named:
                    units[entry.name] = named
            scope = [
                place
                for entry in entries
                for place in (
                    [entry.unit_place(unit) for unit in units[entry.name]]
                    if entry.name in units
                    else [entry.place()]
                )
            ]
            findings.sentence(sentence, scope=scope or None)
    return findings.result()


def claims_about_candidate(sentence: str) -> bool:
    """Whether a sentence of the letter's opening says something about the candidate.

    "An dieser Schnittstelle arbeite ich bereits" and "Next.js ist mir vertraut" do; "mit
    großem Interesse habe ich Ihre Ausschreibung gelesen" and "eine Kombination, die mich
    anspricht" describe the posting, whatever terms they carry.
    """
    return bool(
        FIRST_PERSON_POSSESSIVE.search(POSSESSIVE_IDIOM.sub(" ", sentence))
        or (FIRST_PERSON_SUBJECT.search(sentence) and DOING_VERB.search(sentence))
        or (FIRST_PERSON_OBJECT.search(sentence) and ACQUAINTANCE.search(sentence))
    )


class _Findings:
    def __init__(
        self, master: _Master, posting_terms: list[str], allowed_text: str, posting_names: Sequence[str]
    ) -> None:
        self.master = master
        self.posting_names = _name_forms(posting_names)
        self.allowed_numbers = _numbers(allowed_text)
        self.imported = _imported_terms(posting_terms, master.text)
        self._found: list[str] = []

    def add(self, finding: str) -> None:
        if finding not in self._found:
            self._found.append(finding)

    def result(self) -> list[str]:
        return list(self._found)

    def numbers_only(self, text: str) -> None:
        for number in sorted(_numbers(text) - self.master.numbers - self.allowed_numbers):
            self.add(f"The number {number} does not appear in the master CV.")

    def sentence(self, sentence: str, *, scope: list[_Place] | None) -> None:
        text = _with_digits(sentence)
        durations = {match.group(1) for match in DURATION.finditer(text)}
        self._durations(sentence, text, durations)

        source = self.master.text if scope is None else "\n".join(place.text for place in scope)
        source_numbers = _numbers(source) | self.allowed_numbers
        for number in sorted(_numbers(text) - durations):
            if number in source_numbers:
                continue
            if scope is None or number not in self.master.numbers:
                self.add(f"The number {number} does not appear in the master CV.")
            else:
                self.add(
                    f"The number {number} is tied to {_names(scope)}, but the master CV states it "
                    f"only under {self._where(lambda text: number in _numbers(text))}."
                )

        outside_names = _outside_names(text, self.posting_names)
        for term in self.imported:
            if any(_occurs(term, part) for part in outside_names):
                self.add(f"'{term}' does not appear in the master CV.")
        misplaced: list[str] = []
        for term in self.master.terms:
            if not _occurs(term, text) or _occurs(term, source):
                continue
            if any(_occurs(term, longer) for longer in misplaced):
                continue  # "REST" once "REST API" is reported
            misplaced.append(term)
            # Only reachable with a scope: unscoped, the source is the whole master CV.
            self.add(
                f"'{term}' is tied to {_names(scope)}, but the master CV lists it only under "
                f"{self._where(lambda text: _occurs(term, text))}."
            )

    def no_mixing(self, text: str, *, what: str) -> None:
        mentioned = _mentioned(text, self.master.entries)
        projects = [entry for entry in mentioned if entry.kind == "project"]
        employers = [entry for entry in mentioned if entry.kind == "experience"]
        if projects and employers:
            self.add(
                f"{_names(projects)} and {_names(employers)} appear in {what}, which presents the "
                "project as work done for that employer. The master CV lists it as a separate "
                "project."
            )

    def _durations(self, sentence: str, text: str, durations: set[str]) -> None:
        for years in sorted(durations):
            claims = self.master.durations.get(years)
            if not claims:
                self.add(f"The master CV never claims {years} years of anything ('{sentence.strip()}').")
                continue
            for term in self.master.terms:
                if _occurs(term, text) and not any(_occurs(term, claim) for claim in claims):
                    self.add(
                        f"'{term}' is presented as part of {years} years of experience, but the "
                        f"master CV ties {years} years only to: '{claims[0].strip()}'"
                    )

    def _where(self, holds) -> str:
        places: list[str] = []
        for entry in self.master.entries:
            unit_places = [entry.unit_place(unit) for unit in entry.units if holds(unit.text)]
            if unit_places and not holds(entry.common):
                places.extend(f"'{place.name}'" for place in unit_places)
            elif holds(entry.text):
                places.append(f"'{entry.name}'")
        return "; ".join(places) if places else "its summary or skills section"


def _imported_terms(posting_terms: list[str], master_markdown: str) -> list[str]:
    """The posting's terms the master CV does not back — the ones a model imports.

    A term of several parts ("Next.js / React") is backed when each part is; the parts the
    master CV lacks are what is looked for, so "Next.js / Vue" looks for "Vue". A part too
    short to stand alone ("CI/CD", "UI/UX") keeps the term whole.
    """
    spaced = _normalize(master_markdown)
    squashed = spaced.replace(" ", "")
    imported: list[str] = []
    for term in posting_terms:
        if len(term.split()) > MAX_POSTING_TERM_WORDS:
            continue
        parts = [part.strip() for part in term.split(TERM_PART_SEPARATOR) if part.strip()]
        if len(parts) < 2 or any(len(part) < MIN_TERM_LENGTH for part in parts):
            parts = [term]
        for part in parts:
            if part not in imported and not _is_supported(part, spaced, squashed):
                imported.append(part)
    return imported


def sentence_unit(sentence: str, context: str, master_markdown: str) -> str | None:
    """The unit of the entry `context` names that `sentence` is about, or None.

    By name first ("Für eine Arztpraxis …" names the Arztpraxis system), else by its facts:
    the one unit whose text holds every number and skill the sentence states. A skill no unit
    holds ("Accessibility", listed under skills only) places the sentence nowhere, so it is left
    out here; the fact check reports it on its own. A sentence that names or fits none, or fits
    several, is about the entry as a whole.
    """
    master = _read_master(master_markdown)
    entry = next(iter(_mentioned(context, master.entries)), None)
    if entry is None or not entry.units:
        return None
    named = _mentioned_units(sentence, entry)
    if len(named) == 1:
        return named[0].name
    text = _with_digits(sentence)
    numbers = _numbers(text)
    terms = [
        term
        for term in master.terms
        if _occurs(term, text) and any(_occurs(term, unit.text) for unit in entry.units)
    ]
    if not numbers and not terms:
        return None
    holders = [
        unit
        for unit in entry.units
        if numbers <= _numbers(_with_digits(unit.text)) and all(_occurs(term, unit.text) for term in terms)
    ]
    return holders[0].name if len(holders) == 1 else None


STACK_LINE = re.compile(r"^\s*-?\s*Tech-Stack:\s*(.+?)\.?\s*$", re.M)
VERSION = re.compile(r"\s+\d[\d.]*$")


def unit_stacks(context: str, master_markdown: str) -> list[tuple[str, list[str]]]:
    """The units of the entry `context` names that list a Tech-Stack, each with its technologies.

    "Next.js 16, Nx / pnpm" is ["Next.js", "Nx", "pnpm"]: the versions go, a slash splits.
    """
    master = _read_master(master_markdown)
    entry = next(iter(_mentioned(context, master.entries)), None)
    if entry is None:
        return []
    stacks = []
    for unit in entry.units:
        line = STACK_LINE.search(unit.text)
        if line:
            technologies = [
                VERSION.sub("", part.strip())
                for item in line.group(1).split(",")
                for part in item.split("/")
                if part.strip()
            ]
            stacks.append((unit.name, technologies))
    return stacks


def shared_technologies(stack: list[str], posting_terms: list[str]) -> list[str]:
    """The stack's technologies the posting names, as whole words either way round."""
    return [tech for tech in stack if any(_occurs(tech, term) or _occurs(term, tech) for term in posting_terms)]


def _read_master(master_markdown: str) -> _Master:
    raw: list[tuple[str, str, list[str]]] = []
    for section, lines in _sections(master_markdown):
        kind = (
            "experience"
            if EXPERIENCE_SECTION.search(section)
            else "project" if PROJECT_SECTION.search(section) else "other"
        )
        _, entries = _split_entries(lines)
        for heading, body in entries:
            raw.append((heading, kind, body))

    # A word that names two entries ("Chisinau", "Moldau") tells neither of them apart.
    candidates = [_anchor_words(heading) for heading, _, _ in raw]
    shared = {word for words in candidates for word in words if sum(word in c for c in candidates) > 1}
    entries = []
    for (heading, kind, body), words in zip(raw, candidates):
        common, units = _split_units(body, master_markdown)
        entries.append(
            _Entry(
                name=heading,
                kind=kind,
                text="\n".join([heading, *body]),
                common="\n".join([heading, *common]),
                anchors=frozenset(words - shared),
                units=units,
            )
        )

    terms: list[str] = []
    for item in _skill_items(master_markdown):
        for term in _term_variants(item):
            if len(term) >= MIN_TERM_LENGTH and not term.replace(".", "").isdigit() and term not in terms:
                terms.append(term)

    durations: dict[str, list[str]] = {}
    for sentence in _sentences(master_markdown):
        for match in DURATION.finditer(_with_digits(sentence)):
            durations.setdefault(match.group(1), []).append(_with_digits(sentence))

    return _Master(
        text=master_markdown,
        entries=entries,
        terms=terms,
        numbers=_numbers(master_markdown),
        durations=durations,
    )


def _split_units(body: list[str], master_markdown: str) -> tuple[list[str], tuple[_Unit, ...]]:
    """An entry's lines outside any unit, and the units under its bold subheadings.

    A unit is named by the long words of its subheading that appear nowhere else in the
    master CV: "Bestehendes Verwaltungssystem – Audit, Redesign und Umsetzung" is named by
    "bestehendes" and "Redesign", not by "Umsetzung", which half the CV says.
    """
    common: list[str] = []
    raw: list[tuple[str, list[str]]] = []
    for line in body:
        heading = UNIT_HEADING.match(line)
        if heading:
            raw.append((heading.group(1).strip().rstrip(":"), [line]))
        elif raw:
            raw[-1][1].append(line)
        else:
            common.append(line)

    units = []
    for name, lines in raw:
        text = "\n".join(lines)
        elsewhere = set(_normalize(master_markdown.replace(text, " ")).split())
        words = {word for word in _normalize(PARENTHETICAL.sub(" ", name)).split() if len(word) >= 8}
        units.append(_Unit(name=name, text=text, anchors=frozenset(words - elsewhere)))
    return common, tuple(units)


def _term_variants(item: str) -> list[str]:
    """The skill as listed, plus its leading acronym: "WCAG 2.2 AA" is also "WCAG"."""
    variants = [item]
    words = item.split()
    if len(words) > 1 and re.fullmatch(r"[A-Z]{3,}", words[0]):
        variants.append(words[0])
    return variants


def _anchor_words(heading: str) -> set[str]:
    """The words that name an entry: its employer, or its title when it has no employer.

    "Senior UI/UX Designer — dilotec GmbH, Köln" is named by "dilotec"; job titles repeat
    across entries and a city is not an employer. A project has no employer, so its title
    names it, and only its long words count — "Website" alone would turn every mention of
    the posting company's own website into a mention of the project.
    """
    text = PARENTHETICAL.sub(" ", heading)
    if "—" in text:
        part, min_length = text.split("—", 1)[1].split(",")[0], 5
    else:
        part, min_length = text, 8
    return {word for word in _normalize(part).split() if len(word) >= min_length}


def _mentioned(text: str, entries: list[_Entry]) -> list[_Entry]:
    tokens = _normalize(text).split()
    return [entry for entry in entries if _names_any(tokens, entry.anchors)]


def _mentioned_units(text: str, entry: _Entry) -> list[_Unit]:
    tokens = _normalize(text).split()
    return [unit for unit in entry.units if _names_any(tokens, unit.anchors)]


def _names_any(tokens: list[str], anchors: frozenset[str]) -> bool:
    return any(_names_same(token, anchor) for token in tokens for anchor in anchors)


def _names_same(token: str, anchor: str) -> bool:
    """Whether a word in the text refers to a name word, compounds and inflection included.

    German builds names by compounding: "Kinderarztpraxis" contains "Kinderarzt", and
    "Arztpraxis" shares its head with "Ernährungspraxis". A shared ending of five letters
    between two long words is that head. An inflected form ("bestehend" for "bestehendes")
    differs from the name by an ending of a letter or two. The head alone ("Unternehmen" for
    "Möbelunternehmen") names nothing: it is the word the compound narrows down.
    """
    if token == anchor:
        return True
    # Only the text's word may be much longer: "Sprachen" is not a mention of
    # "Spracherwerb" just because the name starts with it.
    if len(anchor) >= 6 and (token.startswith(anchor) or token.endswith(anchor)):
        return True
    if len(token) >= 6 and anchor.startswith(token) and len(anchor) - len(token) <= 2:
        return True
    if anchor.endswith(token):
        return False
    if min(len(token), len(anchor)) < 9:
        return False
    return _common_suffix(ADJECTIVE_ENDING.sub("", token), ADJECTIVE_ENDING.sub("", anchor)) >= 5


def _common_suffix(a: str, b: str) -> int:
    length = 0
    while length < min(len(a), len(b)) and a[-1 - length] == b[-1 - length]:
        length += 1
    return length


def _occurs(term: str, text: str) -> bool:
    """Whether the term appears in the text as whole words, hyphenated compounds included.

    "Design-System", "Designsystemen" and "WCAG-Audits" carry "Designsysteme" and "WCAG";
    "React" does not occur in "Reactive".
    """
    term_tokens = _normalize(term).split()
    if not term_tokens:
        return False
    tokens = _normalize(text).split()
    width = len(term_tokens)
    squashed = "".join(term_tokens)
    for start in range(len(tokens)):
        if tokens[start : start + width] == term_tokens:
            return True
        for span in range(1, 4):
            if "".join(tokens[start : start + span]) == squashed:
                return True
    return False


def _name_forms(names: Sequence[str]) -> list[list[str]]:
    """Each name as tokens, longest first; a job title also by its core before any qualifier."""
    forms: list[list[str]] = []
    for name in names:
        for form in (PARENTHETICAL.sub(" ", name), TITLE_CORE_END.split(name, 1)[0]):
            tokens = _normalize(form).split()
            if tokens and tokens not in forms:
                forms.append(tokens)
    return sorted(forms, key=len, reverse=True)


def _outside_names(text: str, forms: list[list[str]]) -> list[str]:
    """The text in the pieces left once every occurrence of a name is cut out.

    Kept as pieces so that the words either side of a cut never join into a term.
    """
    words = [word for word in NON_WORD.sub(" ", text).split() if _normalize(word)]
    tokens = [_normalize(word) for word in words]
    pieces: list[list[str]] = [[]]
    start = 0
    while start < len(tokens):
        form = next((f for f in forms if tokens[start : start + len(f)] == f), None)
        if form:
            pieces.append([])
            start += len(form)
        else:
            pieces[-1].append(words[start])
            start += 1
    return [" ".join(piece) for piece in pieces if piece]


def _numbers(text: str) -> set[str]:
    # Markdown emphasis glues to a number ("_06/2014_") and would hide it from the pattern.
    plain = re.sub(r"[_*]", " ", _with_digits(text))
    return {_canonical(match.group(0)) for match in NUMBER.finditer(plain)}


def _canonical(number: str) -> str:
    number = number.replace(",", ".")
    return number if "." in number else str(int(number))


def _with_digits(text: str) -> str:
    def years(match: re.Match[str]) -> str:
        value = match.group(1)
        return f"{NUMBER_WORDS.get(value.casefold(), value)} Jahre"

    text = SPELLED_YEARS.sub(years, text)
    return SPELLED_NUMBER.sub(lambda match: str(NUMBER_WORDS[match.group(1).casefold()]), text)


def _sections(markdown_text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    for line in markdown_text.splitlines():
        match = SECTION.match(line)
        if match:
            sections.append((match.group(1).strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return sections


def _split_entries(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    intro: list[str] = []
    entries: list[tuple[str, list[str]]] = []
    for line in lines:
        match = ENTRY.match(line)
        if match:
            entries.append((match.group(1).strip(), []))
        elif entries:
            entries[-1][1].append(line)
        else:
            intro.append(line)
    return intro, entries


def _sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "---", "<")):
            continue
        sentences.extend(part for part in SENTENCE_END.split(line) if part.strip())
    return sentences


def _names(places: list) -> str:
    return " and ".join(f"'{place.name}'" for place in places)


def fact_check_correction(findings: list[str]) -> str:
    """The findings as an instruction for the next attempt."""
    return "\n".join(
        [
            "## Fact check",
            "Your previous attempt made statements the master CV does not back. Fix every one of "
            "them in this attempt:",
            *(f"- {finding}" for finding in findings),
            "Tie each fact only to the position or project the master CV lists it under. Use only "
            "numbers the master CV states. Keep projects from the Projekte section apart from every "
            "employer. Do not repair a finding by adding anything new.",
            "A sentence that names no employer or project is read as continuing the last one named "
            "in its paragraph. To mention a fact from another position, name that position in the "
            "sentence or start a new paragraph — or leave the fact out.",
            "These instructions are for you only. Never mention them, the master CV, or its "
            "sections in the document itself.",
        ]
    )
