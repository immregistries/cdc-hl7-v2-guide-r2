"""Shared helpers for reading and writing the card tree.

Used by the converter, the quality checks, and the site builder. Needs PyYAML.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO / "cards"
DATA_DIR = REPO / "data"
META = "_meta"

# Conformance verbs, longest first so "SHALL NOT" wins over "SHALL".
VERB_RE = re.compile(r"\b(SHALL NOT|SHOULD NOT|MAY NOT|SHALL|SHOULD|MAY)\b")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_ID_LEN = 80
FOLDER_RE = re.compile(r"^(\d{2})-(.+)$")


# --------------------------------------------------------------------------- text


def clean_text(text: str) -> str:
    """Normalize whitespace from Word: non-breaking spaces, tabs, line breaks."""
    text = text.replace(" ", " ").replace("\t", " ").replace("​", "")
    text = re.sub(r"[ \r\n]+", " ", text)
    return text.strip()


def norm_title(title: str) -> str:
    """Comparison key for titles: case-, punctuation-, and space-insensitive."""
    t = clean_text(title).lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def slugify(text: str, max_len: int = MAX_ID_LEN) -> str:
    text = unicodedata.normalize("NFKD", clean_text(text)).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug or "card"


def find_verbs(text: str) -> list[str]:
    return VERB_RE.findall(text)


ACTOR_HINT = re.compile(
    r"\b(IIS|systems?|submitters?|senders?|receivers?|jurisdictions?|implementers?|implementations?|"
    r"intermediar(?:y|ies)|registr(?:y|ies)|organizations?|local IGs?|EHRs?|providers?|clinicians?|"
    r"programs?|vendors?|trading partners?)\b",
    re.I,
)


def subject_of(text: str) -> str:
    """The grammatical subject before the first conformance verb, without a
    leading condition ('When …, the IIS SHALL' → 'IIS')."""
    m = VERB_RE.search(text)
    if not m:
        return ""
    before = text[: m.start()].strip().rstrip(",")
    if "," in before:
        before = before.rsplit(",", 1)[1].strip()
    before = re.sub(r"^(the|a|an|each|every|all|any|then)\s+", "", before, flags=re.I)
    if not before or len(before.split()) > 6 or re.match(r"^(if|when|where|unless)\b", before, re.I):
        return ""
    return before[0].upper() + before[1:]


def actor_of(text: str) -> str:
    """The party a statement binds, when its subject names one."""
    subject = subject_of(text)
    return subject if ACTOR_HINT.search(subject) else ""


# --------------------------------------------------------------------------- yaml


class _Dumper(yaml.SafeDumper):
    pass


def _str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_representer)


def _indent_lists(self, flow=False, indentless=False):  # noqa: ANN001
    return yaml.SafeDumper.increase_indent(self, flow, False)


_Dumper.increase_indent = _indent_lists  # type: ignore[method-assign]


def dump_yaml(data) -> str:
    return yaml.dump(
        data,
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        width=100000,
        default_flow_style=False,
    )


def write_yaml(path: Path, data, header: str | None = None) -> None:
    text = dump_yaml(data)
    if header:
        text = "".join(f"# {line}\n" if line else "#\n" for line in header.splitlines()) + text
    write_text(path, text)


def read_yaml(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return default if data is None else data


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --------------------------------------------------------------------------- tree


@dataclass
class Card:
    id: str
    title: str
    path: Path
    order: int
    depth: int
    meta: dict
    narrative: str = ""
    statements: list = field(default_factory=list)
    children: list["Card"] = field(default_factory=list)
    parent: "Card | None" = None
    number: str = ""

    @property
    def paragraphs(self) -> list[str]:
        """Narrative blocks separated by blank lines (paragraphs and lists)."""
        return [b for b in re.split(r"\n\s*\n", self.narrative.strip()) if b.strip()]

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


def _load_dir(directory: Path, depth: int, parent: Card | None) -> list[Card]:
    cards = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        m = FOLDER_RE.match(entry.name)
        meta = read_yaml(entry / "card.yml", {})
        if not m or not meta.get("id"):
            raise ValueError(f"Not a card folder (needs NN- prefix and card.yml with id): {entry}")
        narrative_path = entry / "narrative.md"
        card = Card(
            id=meta["id"],
            title=meta.get("title", ""),
            path=entry,
            order=int(m.group(1)),
            depth=depth,
            meta=meta,
            narrative=narrative_path.read_text(encoding="utf-8") if narrative_path.exists() else "",
            statements=read_yaml(entry / "statements.yml", []),
            parent=parent,
        )
        card.children = _load_dir(entry, depth + 1, card)
        cards.append(card)
    return cards


def load_tree(cards_dir: Path = CARDS_DIR) -> list[Card]:
    """Load the card tree. Returns top-level cards, with display numbers set."""
    roots = _load_dir(cards_dir, 1, None)

    def number(cards: list[Card], prefix: str) -> None:
        for i, card in enumerate(cards, 1):
            card.number = f"{prefix}{i}"
            number(card.children, card.number + ".")

    number(roots, "")
    return roots


def walk(roots: list[Card]):
    for root in roots:
        yield from root.walk()
