"""The narrative crosswalk with Release 1.5: quality/r15/narrative/*.yml.

Each file compares part of the 2018 narrative with this guide, one item per piece of guidance (see the header of
01-02-introduction-and-actors.yml for the fields). load() reads the files in name order and checks every item: known
result, unique ID, and guide references that name an existing card or statement.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from pathlib import Path

from guidecards import read_yaml

RESULTS = {  # result: (label, help)
    "changed": ("Changed", "This guide says something different."),
    "dropped": ("Not carried forward", "Not in this guide."),
    "partial": ("Partly carried forward", "Some of it is in this guide."),
    "expanded": ("Expanded", "This guide keeps it and goes further."),
    "same": ("Same", "This guide says the same thing (the wording may differ)."),
    "format": ("Format", "About message format or validation; the profiles govern it and are compared above."),
    "context": ("Background", "Background or document organization, with nothing to carry forward."),
}
ATTENTION = ("changed", "dropped", "partial")
FIELDS = ["id", "chapter", "section", "page", "verb", "result", "r15", "guide", "note", "recommendation"]


def _ref_card(ref: str) -> str:
    return ref.split("--s", 1)[0] if "--s" in ref else ref


def load(repo: Path, by_id: dict) -> list[dict]:
    """The crosswalk files, in name order. Raises SystemExit on an unknown result, a duplicate ID, or a bad reference."""
    folder = repo / "quality" / "r15" / "narrative"
    statements = {s["id"] for c in by_id.values() for s in c.statements}
    parts, seen = [], set()
    for path in sorted(folder.glob("*.yml")) if folder.exists() else []:
        data = read_yaml(path, {}) or {}
        for it in data.get("items", []):
            where = f"{path.name}: {it.get('id')}"
            if it["id"] in seen:
                raise SystemExit(f"{where}: duplicate item id")
            seen.add(it["id"])
            if it.get("result") not in RESULTS:
                raise SystemExit(f"{where}: unknown result {it.get('result')}")
            for ref in it.get("guide") or []:
                if _ref_card(ref) not in by_id or ("--s" in ref and ref not in statements):
                    raise SystemExit(f"{where}: unknown guide reference {ref}")
        for seg, n in (data.get("read") or {}).items():
            if set(n) != {"notes", "format", "duplicate"} or n["format"] + n["duplicate"] > n["notes"]:
                raise SystemExit(f"{path.name}: read counts for {seg} need notes >= format + duplicate")
        data["file"] = path.name
        parts.append(data)
    return parts


def items(parts: list[dict]):
    for p in parts:
        for it in p.get("items", []):
            yield p, it


def is_field_notes(part: dict) -> bool:
    """Pass 2 parts (field notes) carry per-segment `read` counts."""
    return "read" in part


def counts(parts: list[dict]) -> Counter:
    return Counter(it["result"] for _, it in items(parts))


def to_csv(parts: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(FIELDS)
    for p, it in items(parts):
        row = {**it, "chapter": p.get("chapter", ""), "guide": " ".join(it.get("guide") or [])}
        w.writerow([str(row.get(f, "") or "").strip() for f in FIELDS])
    return buf.getvalue()
