#!/usr/bin/env python3
"""Filter terms for the navigation filter: what each section is about, by field, code, and concept.

Two kinds of terms:

- Automatic, computed on every build from the card's own text: field references (RXA-20, PID-5.7),
  profile codes (Z22), message types (VXU), value set IDs, LOINC codes, and the code values the text
  uses (RE, NB, 998, …).
- Curated, in cards/_meta/filter-terms.yml (card ID → terms): concepts a reader filters by that the
  text does not always spell out the same way (refusal, VFC, consent, forecast, …). Edit this file by
  hand; it survives re-conversion because card IDs are stable.

    python tools/filter_terms.py --draft     # add draft terms for cards that have none in the file

The draft comes from VOCABULARY below: a concept is suggested when it appears in the card's title or its
parent's title, or at least twice in the card's statements and narrative. Cards already in the file are left alone
(use --redraft to replace every entry).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guidecards import CARDS_DIR, META, load_tree, read_yaml, walk, write_text  # noqa: E402

TERMS_FILE = CARDS_DIR / META / "filter-terms.yml"
FIELD_RE = re.compile(r"\b([A-Z][A-Z0-9]{2})-(\d{1,2})((?:\.\d{1,2}){0,2})\b")
NOT_SEGMENTS = {"HTI", "SPD"}
QUOTED_CODE_RE = re.compile(r"['\"‘’“”]([A-Z0-9]{1,8})['\"‘’“”]")
LOINC_RE = re.compile(r"\b\d{4,5}-\d\b")
CVX_RE = re.compile(r"\b(?:CVX|code)\s+(\d{2,3})\b")
VS_RE = re.compile(r"\b(PHVS_[A-Za-z0-9_]+|HL7\d{4}(?:_[A-Z0-9]+)?|CDCREC|NIP\d{3})\b")
MSG_RE = re.compile(r"\b(VXU|QBP|RSP|ACK)\b")
PROFILE_RE = re.compile(r"\b(Z(?:22|23|31|32|33|34|42|44))\b")

# Concept vocabulary for the curated draft: term → patterns (case-insensitive regular expressions).
VOCABULARY: dict[str, list[str]] = {
    # patient identity
    "patient identifier": [r"patient identifier", r"\bMRN\b", r"medical record number", r"PID-3\b"],
    "registry identifier": [r"state registry id", r"registry identifier", r"\bSR\b"],
    "patient matching": [r"patient matching", r"record matching", r"\bmatch(?:ing|ed)?\b"],
    "deduplication": [r"dedup", r"duplicate"],
    "patient name": [r"patient name", r"PID-5\b"],
    "official registry name": [r"official registry name", r"'L' name", r"legal name"],
    "newborn": [r"newborn", r"placeholder name"],
    "maiden name": [r"maiden name"],
    "nickname/alias": [r"nickname", r"\balias"],
    "special characters": [r"diacritic", r"special character", r"translitera"],
    "date of birth": [r"date of birth", r"birth date", r"\bDOB\b", r"PID-7\b"],
    "address": [r"(?:patient|mailing|home|residential|street) address", r"address type", r"PID-11\b"],
    "no fixed address": [r"fixed address", r"homeless"],
    "phone": [r"\bphone", r"telephone"],
    "email": [r"\bemail", r"e-mail"],
    "race": [r"\brace\b", r"PID-10\b"],
    "ethnicity": [r"ethnicit", r"PID-22\b"],
    "MENA": [r"\bMENA\b", r"Middle Eastern"],
    "guardian/next of kin": [r"guardian", r"next.of.kin", r"\bNK1\b"],
    "consent": [r"consent", r"opt-in", r"opt-out", r"\bopt in\b", r"\bopt out\b"],
    "protection indicator": [r"protection indicator", r"PD1-12\b"],
    "patient status": [r"active status", r"inactive status", r"moved or gone elsewhere", r"\bdeceased"],
    # vaccines and doses
    "CVX": [r"\bCVX\b"],
    "NDC": [r"\bNDC\b"],
    "MVX/manufacturer": [r"\bMVX\b", r"manufacturer"],
    "lot number": [r"lot number"],
    "expiration date": [r"expiration date"],
    "combination vaccine": [r"combination vaccine"],
    "unspecified formulation": [r"unspecified formulation"],
    "non-US vaccine": [r"non-US", r"foreign", r"international"],
    "inactive code": [r"inactive (?:code|CVX)", r"never active"],
    "administered dose": [r"administered (?:dose|vaccination)", r"new administration", r"RXA-9\.1 (?:=|of|is)?\s*'?00"],
    "historical dose": [r"historical"],
    "refusal": [r"refus"],
    "contraindication": [r"contraindicat"],
    "precaution": [r"precaution"],
    "immunity": [r"immunity", r"serolog", r"history of disease"],
    "adverse event": [r"adverse (?:event|reaction)", r"\bVAERS\b"],
    "patient condition": [r"patient condition", r"patient-level condition"],
    "indication": [r"\bindication"],
    "funding source": [r"funding source", r"stock model", r"\bstock\b"],
    "eligibility": [r"eligibilit"],
    "VFC": [r"\bVFC\b", r"Vaccines for Children"],
    "VIS": [r"\bVIS\b", r"vaccine information statement"],
    "route and site": [r"\broute\b", r"administration site", r"body site", r"RXR-[12]\b"],
    "dose amount": [r"administered amount", r"dose volume", r"RXA-6\b"],
    "date of administration": [r"date of administration", r"administration date", r"date of vaccination", r"RXA-3\b"],
    "time zone": [r"time zone", r"time-zone", r"\boffset", r"\bUTC\b"],
    "update": [r"\bupdates? (?:message|record|workflow)", r"\bmodif(?:y|ying|ication)", r"simple update", r"RXA-21=?U\b", r"'U'"],
    "delete": [r"\bdeletion", r"\bdelete (?:message|record)", r"RXA-21=?D\b", r"'D'"],
    "action code": [r"action code", r"RXA-21\b"],
    # observations and CDS
    "order segment group": [r"order segment group"],
    "observation": [r"\bOBX\b", r"observation"],
    "co-constraints": [r"co-constraint"],
    "LOINC": [r"\bLOINC\b"],
    "SNOMED CT": [r"SNOMED"],
    "forecast": [r"forecast", r"recommended date", r"due date"],
    "evaluation": [r"\bevaluation", r"dose validity", r"evaluated (?:history|dose|series)"],
    "clinical decision support": [r"\bCDS\b", r"clinical decision support", r"\bCDSi\b"],
    "schedule": [r"\bACIP\b", r"schedule"],
    # messaging
    "acknowledgement": [r"acknowledg", r"\bACK\b", r"MSA-1\b"],
    "error": [r"\berrors?\b", r"\bERR\b"],
    "severity": [r"severity", r"ERR-4\b"],
    "query": [r"\bquer(?:y|ies)\b", r"\bQBP\b"],
    "response": [r"\bRSP\b", r"query response", r"response profile"],
    "candidate list": [r"candidate"],
    "no match": [r"no person record", r"not found", r"\bNF\b"],
    "too many matches": [r"too many", r"\bTM\b"],
    "submitting organization": [r"submitting organization", r"sending facility", r"MSH-4\b"],
    "responsible organization": [r"responsible organization", r"MSH-22\b"],
    "administering organization": [r"administering organization", r"RXA-11\b"],
    "entering organization": [r"entering organization", r"ORC-17\b"],
    "provider": [r"\bprovider"],
    "record identity": [r"filler order number", r"ORC-3\b", r"source record"],
    "transport": [r"transport", r"\bSOAP\b", r"\bWSDL\b", r"web service"],
    "authentication": [r"authenticat", r"credential"],
    "security": [r"security", r"enumeration"],
    "data quality": [r"data quality"],
    "onboarding": [r"onboarding"],
    "local implementation guide": [r"local (?:implementation )?guide", r"local IG", r"jurisdiction-specific"],
    "certification": [r"certification", r"\bONC\b", r"\bHTI-[12]\b"],
    "versioning": [r"\bversion(?:s|ing)?\b"],
    "usage": [r"usage designation", r"required but may be empty", r"\bRE\b usage"],
    "cardinality": [r"cardinalit"],
    "data type flavor": [r"\bflavors?\b"],
    "value set": [r"value set", r"code set"],
    "encoding characters": [r"encoding character", r"delimiter", r"escape sequence", r"line terminator"],
}
MAX_CURATED = 8


def card_text(c) -> tuple[str, str, str]:
    caps = " ".join(f.get("caption", "") for f in c.meta.get("figures", []))
    return c.title, " ".join(s["text"] for s in c.statements), c.narrative + " " + caps


def auto_terms(c, segment_names: set[str] | None = None) -> list[str]:
    """Terms found literally in the card: fields, profiles, message types, value sets, LOINC and other codes."""
    title, statements, narrative = card_text(c)
    text = " ".join((title, statements, narrative))
    out: list[str] = []

    def add(t):
        if t and t not in out:
            out.append(t)

    for m in FIELD_RE.finditer(text):
        if m.group(1) in NOT_SEGMENTS or (segment_names is not None and m.group(1) not in segment_names):
            continue
        add(f"{m.group(1)}-{m.group(2)}")
        if m.group(3):
            add(f"{m.group(1)}-{m.group(2)}{m.group(3)}")
    for rx in (PROFILE_RE, MSG_RE, VS_RE):
        for m in rx.finditer(text):
            add(m.group(1))
    for m in LOINC_RE.finditer(text):
        add(m.group(0))
    for m in CVX_RE.finditer(text):
        add(m.group(1))
    for m in QUOTED_CODE_RE.finditer(text):
        add(m.group(1))
    return out


def draft_terms(c) -> list[str]:
    """Suggest concepts: in the card's title or its parent's title, or mentioned at least twice in the card."""
    title, statements, narrative = card_text(c)
    parent_title = c.parent.title if c.parent is not None else ""
    scored = []
    for term, patterns in VOCABULARY.items():
        rxs = [re.compile(p, re.I) for p in patterns]
        in_title = any(r.search(title) for r in rxs)
        in_parent = any(r.search(parent_title) for r in rxs)
        mentions = sum(len(r.findall(statements)) + len(r.findall(narrative)) for r in rxs)
        if in_title or in_parent or mentions >= 2:
            scored.append((-(100 * in_title + 50 * in_parent + mentions), term))
    return [t for _, t in sorted(scored)[:MAX_CURATED]]


def load_curated(path: Path = TERMS_FILE) -> dict[str, list[str]]:
    data = read_yaml(path, {}) or {}
    return {k: [str(x) for x in (v or [])] for k, v in data.items()}


def write_curated(path: Path, data: dict[str, list[str]], order: list[str]) -> None:
    lines = ["# Curated filter terms, by card ID (see tools/filter_terms.py).",
             "# These are what a reader can filter the contents by, besides the title and the fields, codes, and",
             "# value sets the card mentions (those are added automatically). Edit freely: add, remove, or reword.",
             "# The first version was a machine draft (12 Nov 2026) for review.", ""]
    for cid in order:
        if cid in data:
            terms = ", ".join(f'"{t}"' if re.search(r"[:,#'\"\[\]{}]", t) else t for t in data[cid])
            lines.append(f"{cid}: [{terms}]")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--draft", action="store_true", help="add draft terms for cards not yet in the file")
    ap.add_argument("--redraft", action="store_true", help="replace every entry with a fresh draft")
    args = ap.parse_args()
    cards = list(walk(load_tree(CARDS_DIR)))
    curated = {} if args.redraft else load_curated()
    if args.draft or args.redraft:
        added = 0
        for c in cards:
            if c.id not in curated:
                curated[c.id] = draft_terms(c)
                added += 1
        write_curated(TERMS_FILE, curated, [c.id for c in cards])
        print(f"Drafted terms for {added} cards; {sum(len(v) for v in curated.values())} curated terms in {TERMS_FILE.name}.")
    n_auto = sum(len(auto_terms(c)) for c in cards)
    print(f"{len(cards)} cards: {sum(len(v) for v in curated.values())} curated terms, {n_auto} automatic terms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
