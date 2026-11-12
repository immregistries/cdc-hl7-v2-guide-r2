#!/usr/bin/env python3
"""Import the example messages into examples/ (one YAML file per example).

    python tools/import_examples.py      # paths from inputs.json (examples_docx, examples_xlsx)

Inputs (kept local, never committed):
- CDC's example list (xlsx): what each example should show, the guide sub-section it belongs to, status.
- The drafted sample messages (docx): a VXU base message, then examples under Heading 1/Heading 2. Most
  examples are clips (only the segments that matter); some are complete messages or message sequences.

Each example is matched to its row in the list and, through the row's "IG Sub-Section", to cards. Clips
are assembled into complete messages from a base (tools/hl7msg.py) so that every example can be checked
against the profiles and shown whole, with the clipped part highlighted.

Corrections go in examples/_meta/overrides.yml (card assignments, row matches, bases, skips). Re-runs
are deterministic, and example IDs are kept in examples/_meta/ids.yml.
Word comments in the docx and the list's Notes column are review notes and are not imported.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hl7msg  # noqa: E402
from guidecards import CARDS_DIR, REPO, load_tree, norm_title, read_yaml, slugify, walk, write_text, write_yaml  # noqa: E402

EX_DIR = REPO / "examples"
META_DIR = EX_DIR / "_meta"
STATUSES = ("Drafted", "Question", "Need help", "Not sure what was envisioned", "Done", "Final")
STOP = {"the", "a", "an", "of", "and", "in", "for", "with", "to", "v", "vs", "msg", "message", "example", "examples"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+(?:-[0-9]+)?", (text or "").lower()) if w not in STOP}


def similarity(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb)) * 0.7 + difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() * 0.3


# ---------------------------------------------------------------- the list (xlsx)

def read_list(path: Path) -> list[dict]:
    import openpyxl
    ws = openpyxl.load_workbook(path, data_only=True).active
    rows, section, header, item, name, sub = [], None, {}, None, None, None
    for n, raw in enumerate(ws.iter_rows(values_only=True), 1):
        cells = [("" if c is None else str(c)).strip() for c in raw]
        if not any(cells):
            continue
        second = cells[1] if len(cells) > 1 else ""
        if second in ("Name", "Example to show", "Example", "Messages") and any(c in ("IG Sub-Section", "IG Section") for c in cells):
            section, header = cells[0], {h: i for i, h in enumerate(cells) if h}
            item = name = sub = None
            continue
        if not header:
            continue
        get = lambda *keys: next((cells[header[k]] for k in keys if k in header and header[k] < len(cells)), "")  # noqa: E731
        if cells[0]:
            item, name, sub = cells[0], get("Name"), None
        example = get("Example to show", "Example", "Messages")
        s = get("IG Sub-Section", "IG Section")
        if s:
            sub = s
        status = next((c for c in cells if c in STATUSES), "")
        rows.append({"row": n, "section": section, "item": item, "name": name, "example": example,
                     "sub_section": sub or "", "status": status})
    return rows


# ---------------------------------------------------------------- the samples (docx)

def read_samples(path: Path) -> list[dict]:
    """Entries: {group, title, blocks: [{label, segments}], notes, ig_section}."""
    import docx
    doc = docx.Document(path)
    entries, group, cur = [], None, None

    def start(title, level):
        nonlocal cur
        cur = {"group": group, "title": title, "level": level, "blocks": [], "notes": [], "ig_section": None, "_label": []}
        entries.append(cur)

    for p in doc.paragraphs:
        text = p.text.replace(" ", " ").strip()
        if not text:
            continue
        style = p.style.name
        is_seg = bool(hl7msg.segments(text))
        if style.startswith("Heading") and not is_seg:
            level = int(re.sub(r"\D", "", style) or 1)
            title = " ".join(text.split())
            if level == 1:
                group = title
            start(title, level)
            continue
        if cur is None:
            start("Untitled", 1)
        if is_seg:
            segs = hl7msg.segments(text)
            if cur["_label"] or not cur["blocks"]:
                cur["blocks"].append({"label": " ".join(cur["_label"]).rstrip(":").strip(), "segments": segs})
                cur["_label"] = []
            else:
                cur["blocks"][-1]["segments"].extend(segs)
            continue
        m = re.match(r"^IG Section:\s*(.+)$", text)
        if m:
            cur["ig_section"] = m.group(1).strip()
            continue
        if re.match(r"^Example to show\b", text):
            continue
        cur["_label"].append(text)
    for e in entries:
        # a complete message followed by labelled clips is one annotated message (e.g. a long RSP)
        if len(e["blocks"]) > 1 and e["blocks"][0]["segments"][0].startswith("MSH") \
                and not any(b["segments"][0].startswith("MSH") for b in e["blocks"][1:]):
            first = e["blocks"][0]
            for b in e["blocks"][1:]:
                if b["label"]:
                    e["notes"].append(b["label"])
                first["segments"].extend(b["segments"])
            e["blocks"] = [first]
        # trailing prose (after the last segment block) is a note; labels that never preceded segments too
        if e["_label"]:
            e["notes"].extend(e["_label"])
        del e["_label"]
        # a label that reads as a sentence explaining the example becomes a note when there is only one block
        if len(e["blocks"]) == 1 and e["blocks"][0]["label"] and len(e["blocks"][0]["label"]) > 60:
            e["notes"].insert(0, e["blocks"][0]["label"])
            e["blocks"][0]["label"] = ""
    return [e for e in entries if e["blocks"] or e["notes"]]


# ---------------------------------------------------------------- build

def card_index():
    cards = list(walk(load_tree(CARDS_DIR)))
    return cards, {norm_title(c.title): c for c in cards}


def resolve_cards(text: str, by_title: dict, cards) -> tuple[list[str], list[str]]:
    ids, missing = [], []
    for part in [p.strip() for p in re.split(r";|\n", text or "") if p.strip()]:
        key = norm_title(part)
        c = by_title.get(key)
        if c is None:
            best = max(cards, key=lambda c: difflib.SequenceMatcher(None, norm_title(c.title), key).ratio())
            if difflib.SequenceMatcher(None, norm_title(best.title), key).ratio() >= 0.82:
                c = best
        if c is None:
            missing.append(part)
        elif c.id not in ids:
            ids.append(c.id)
    return ids, missing


def match_row(entry_title: str, group: str, rows: list[dict], used: set[int]) -> dict | None:
    item_codes = set(re.findall(r"\b[A-Z][A-Z0-9]{2}-\d+\b", group or ""))
    best, score = None, 0.0
    for r in rows:
        s = similarity(entry_title, r["example"] or r["item"] or "")
        if item_codes and r["item"] in item_codes:
            s += 0.25
        if r["row"] in used:
            s -= 0.2
        s = max(s, similarity(entry_title, (r["item"] or "") + " " + (r["name"] or "")) * 0.8)
        if s > score:
            best, score = r, s
    return best if score >= 0.5 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--docx", type=Path)
    ap.add_argument("--xlsx", type=Path)
    args = ap.parse_args()
    inputs = json.loads((REPO / "inputs.json").read_text(encoding="utf-8")) if (REPO / "inputs.json").exists() else {}
    docx_path = args.docx or Path(inputs["examples_docx"])
    xlsx_path = args.xlsx or Path(inputs["examples_xlsx"])

    rows = read_list(xlsx_path)
    entries = read_samples(docx_path)
    overrides = read_yaml(META_DIR / "overrides.yml", {}) or {}
    ids_ledger = read_yaml(META_DIR / "ids.yml", {}) or {}
    cards, by_title = card_index()

    # bases
    vxu_base = next(e for e in entries if e["title"].lower().startswith("vxu base"))
    bases = {"vxu-base": vxu_base["blocks"][0]["segments"]}
    rsp_base = next((e for e in entries if e["title"].lower() == "base message"), None)
    if rsp_base:
        bases["rsp-base"] = rsp_base["blocks"][0]["segments"]
    ack_full = next((e for e in entries if any(hl7msg.seg_type(s) == "MSA" for b in e["blocks"] for s in b["segments"])
                     and e["blocks"][0]["segments"][0].startswith("MSH") and "ERR" in {hl7msg.seg_type(s) for s in e["blocks"][0]["segments"]}), None)
    if ack_full:
        bases["ack-base"] = [s for s in ack_full["blocks"][0]["segments"] if hl7msg.seg_type(s) != "ERR"]

    examples, used_rows = [], set()
    for e in entries:
        if e is vxu_base:
            title, group = "VXU base message", e["group"]
        else:
            title, group = e["title"], e["group"]
        if not e["blocks"]:
            continue
        if e is rsp_base:
            title = "Z32/Z42 base message"
        # sequences vs variants
        types = [hl7msg.get(b["segments"][0], 9, 1, 1) if b["segments"][0].startswith("MSH") else None for b in e["blocks"]]
        in_seq_group = bool(group and re.search(r"sequence|flow|correction after", group, re.I)) or bool(re.search(r"flow|correction after|delete \+ add|^update$", title, re.I))
        sequence = len(e["blocks"]) > 1 and (in_seq_group or len({t for t in types if t}) > 1)
        parts = [(title, e["blocks"])] if sequence or len(e["blocks"]) == 1 else \
            [((f"{title}: {b['label']}" if b["label"] else f"{title} ({k})"), [b]) for k, b in enumerate(e["blocks"], 1)]
        for ptitle, blocks in parts:
            key = f"{group} / {ptitle}" if group and group != ptitle else ptitle
            ov = (overrides.get("examples") or {}).get(key, {})
            if ov.get("skip"):
                continue
            row = None
            if "row" in ov:
                row = next((r for r in rows if r["row"] == ov["row"]), None)
            elif e is not vxu_base and e is not rsp_base:
                row = match_row(ptitle, group, rows, used_rows) or match_row(group or "", group, rows, used_rows)
            if row:
                used_rows.add(row["row"])
            used_rows.update(ov.get("also") or [])
            sub = ov.get("sections") or (row["sub_section"] if row else "") or e["ig_section"] or ""
            card_ids, missing = resolve_cards(sub, by_title, cards)
            if ov.get("cards"):
                card_ids = ov["cards"]
            messages = []
            for b in blocks:
                clip = b["segments"]
                if hl7msg.complete(clip):
                    base_id = None
                else:
                    first = hl7msg.seg_type(clip[0])
                    base_id = ov.get("base") or ("ack-base" if first in ("ERR", "MSA") else
                                                 "rsp-base" if (group or "").startswith("Z32/Z42") else "vxu-base")
                segs, from_clip = hl7msg.assemble(bases.get(base_id, []), clip) if base_id else (clip, list(range(len(clip))))
                messages.append({"label": b["label"], "base": base_id, "clip": clip, "segments": segs, "from_clip": from_clip})
            eid = ids_ledger.get(key) or slugify(ptitle if not group or ptitle.lower().startswith(group.lower()) else f"{group} {ptitle}", 56)
            n = 2
            while eid in {x["id"] for x in examples}:
                eid = f"{eid[:56]}-{n}"
                n += 1
            ids_ledger[key] = eid
            focus = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{2}-\d+(?:\.\d+)?\b", f"{row['item'] if row else ''} {group} {ptitle}")))
            examples.append({
                "id": eid, "title": ptitle, "group": group or "",
                "kind": "base" if e in (vxu_base, rsp_base) else ("sequence" if sequence else "example"),
                "profile": next((hl7msg.profile_of(m["segments"]) for m in messages if hl7msg.profile_of(m["segments"])), None),
                "cards": card_ids, "unresolved_sections": missing,
                "list": ({k: row[k] for k in ("row", "section", "item", "example", "sub_section", "status")} if row else None),
                "focus": focus, "notes": e["notes"] if len(parts) == 1 else [], "messages": messages, "source_key": key,
            })

    # base examples belong on the profile cards
    for ex in examples:
        if ex["kind"] == "base" and not ex["cards"]:
            ex["cards"] = [c.id for c in cards if c.id == ("vaccination-record-update-vxu-message-profile" if ex["id"].startswith("vxu") else "response-rsp-profiles")]

    # write
    EX_DIR.mkdir(exist_ok=True)
    for old in EX_DIR.glob("*.yml"):
        old.unlink()
    for n, ex in enumerate(examples, 1):
        data = {k: v for k, v in ex.items() if v not in (None, [], "", {})}
        for m in data["messages"]:
            m["clip"] = "\n".join(m["clip"])
            m["message"] = "\n".join(m.pop("segments"))
            if not m.get("label"):
                m.pop("label", None)
            if not m.get("base"):
                m.pop("base", None)
        write_yaml(EX_DIR / f"{n:03d}-{ex['id'][:40]}.yml", data, header="Generated by tools/import_examples.py from the example list and sample messages. Do not edit by hand before cutover; use examples/_meta/overrides.yml.")
    write_yaml(META_DIR / "ids.yml", dict(sorted(ids_ledger.items())), header="Example IDs by source heading. Never reuse an ID.")
    write_yaml(META_DIR / "bases.yml", {k: "\n".join(v) for k, v in bases.items()}, header="Base messages used to assemble clipped examples (from the sample messages).")
    # a sequence covers every list row of its item (one row per message)
    for ex in examples:
        if ex["kind"] == "sequence" and ex["list"]:
            used_rows.update(r["row"] for r in rows if r["section"] == ex["list"]["section"] and r["item"] == ex["list"]["item"])
    unmatched = [r for r in rows if r["row"] not in used_rows]
    write_yaml(META_DIR / "list.yml", {"rows": rows, "unmatched_rows": [r["row"] for r in unmatched]},
               header="CDC's example list, as imported (Notes column left out). unmatched_rows have no example yet.")
    if not (META_DIR / "overrides.yml").exists():
        write_text(META_DIR / "overrides.yml", "# Corrections for tools/import_examples.py, keyed by 'Heading 1 / Heading 2' (see ids.yml).\n"
                   "# Per example: row (list row number), sections (IG sub-section titles, ';'-separated), cards (card IDs),\n"
                   "# base (vxu-base | rsp-base | ack-base), skip (true).\nexamples: {}\n")
    print(f"{len(examples)} examples ({sum(e['kind'] == 'sequence' for e in examples)} sequences) from {len(entries)} headings; "
          f"{len(rows)} list rows, {len(unmatched)} without an example; "
          f"{sum(1 for e in examples if not e['cards'])} examples without a card.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
