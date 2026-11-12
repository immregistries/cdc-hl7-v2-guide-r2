"""Narrative ↔ IGAMT structure comparison (called from check_cards.py).

Three kinds of results:

1. Automated cross-checks between the cards and model/ (the normalized IGAMT
   export): field references that do not exist, field names that differ from
   the HL7 names, codes the text uses that are not in the value sets bound to
   the field, and Figure 20 against the OBX co-constraint tables.
2. Automated checks of the export itself (IGAMT change requests): conditional
   usage without a predicate, empty or placeholder value sets, reused
   constraint IDs, inconsistent co-constraint rows, and similar.
3. Reviewed findings in quality/igamt-review.yml: judgements a reviewer made
   with the evidence in hand (conflicts, gaps, confirmations).

It also returns a per-card cross-reference of the fields each card mentions and
what the profiles say about them, which the site shows on each card.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from guidecards import read_yaml
from structure_index import FIELD_RE, PROFILE_ORDER, Model

CATEGORIES = {
    "igamt": "Narrative and IGAMT structure",
    "igamt-export": "IGAMT export (change requests)",
}
QUOTE = "'\"‘’“”"
CODE = r"([A-Z0-9][A-Za-z0-9]{0,8})"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _similar(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return True
    if a in b or b in a:
        return True
    ta, tb = set(a.split()) - {"of", "the", "and", "a"}, set(b.split()) - {"of", "the", "and", "a"}
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.6


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;])\s+|\n+", text) if s.strip()]


def card_texts(card) -> list[tuple[str | None, str]]:
    """(statement id or None, text) for the narrative and statements of a card."""
    out = [(None, p) for p in card.paragraphs]
    out += [(s["id"], s["text"]) for s in card.statements]
    return out


# ---------------------------------------------------------------- field references

NAME_AFTER = re.compile(r"^\s*\(([^)]{3,60})\)")
NAME_AFTER_BARE = re.compile(r"^\s+(?:[-–—]\s+)?((?:[A-Z][\w/'-]*\s?){1,6})")
NAME_BEFORE = re.compile(r"((?:[A-Z][\w/'-]*\s){1,5})\(\s*$")


def code_claims(sentence: str, ref_end: int, ref_start: int) -> list[str]:
    """Codes the sentence assigns to the field reference at [ref_start, ref_end)."""
    after = sentence[ref_end:ref_end + 80]
    before = sentence[max(0, ref_start - 60):ref_start]
    codes = []
    q = f"[{QUOTE}]?"
    for pat in (rf"^\s*(?:=|is set to|values? of|value|severity|is valued(?: with)?|SHALL contain(?: the value)?)\s*{q}{CODE}{q}(?=[\s.,;:)]|$)",
                rf"^\s*code\s+{CODE}\b"):
        m = re.search(pat, after)
        if m:
            codes.append(m.group(1))
    m = re.search(rf"[{QUOTE}]{CODE}[{QUOTE}]\s+in\s+(?:the\s+)?$", before)
    if m:
        codes.append(m.group(1))
    m = re.search(rf"\b(?:CVX|code)\s+(\d{{2,4}})\s+in\s+(?:the\s+)?$", before)
    if m:
        codes.append(m.group(1))
    m = re.search(r"^\s*(?:MAY|SHOULD|SHALL)?\s*(?:be\s+)?(?:omitted\s+or\s+)?populated\s+with\s+((?:[A-Z0-9]{2,8}(?:,\s+or\s+|,\s*|\s+or\s+)?)+)", after)
    if m:
        codes += re.findall(r"[A-Z0-9]{2,8}", m.group(1))
    return [c for c in codes if c not in ("SHALL", "SHOULD", "MAY", "NOT", "VXU", "QBP", "RSP", "ACK")]


def collect_refs(cards) -> list[dict]:
    refs = []
    for c in cards:
        for sid, text in card_texts(c):
            for s in sentences(text):
                for m in FIELD_RE.finditer(s):
                    comp = m.group(3).split(".")[1] if m.group(3) else None
                    refs.append({
                        "card": c.id, "statement": sid, "sentence": " ".join(s.split()),
                        "segment": m.group(1), "field": int(m.group(2)), "component": int(comp) if comp else None,
                        "text": m.group(0), "start": m.start(), "end": m.end(),
                        "name_after": (NAME_AFTER.match(s[m.end():]) or [None, None])[1],
                        "name_before": (NAME_BEFORE.search(s[:m.start()]) or [None, None])[1],
                        "codes": code_claims(s, m.end(), m.start()),
                    })
    return refs


def field_xref(model: Model, refs: list[dict]) -> dict[str, list[dict]]:
    """Per card: the fields it mentions (first-mention order) and the XML facts for each."""
    out: dict[str, list[dict]] = defaultdict(list)
    seen = set()
    for r in refs:
        key = (r["card"], r["segment"], r["field"])
        if key in seen or r["segment"] not in model.segment_names or not model.field_exists(r["segment"], r["field"]):
            continue
        seen.add(key)
        seg, pos = r["segment"], r["field"]
        usage = [{"usage": u, "where": where} for where, u in model.usage_summary(seg, pos)]
        cons = []
        for c in model.constraints_by_field.get((seg, pos), []):
            if c["id"] not in [x["id"] for x in cons]:
                cons.append({"id": c["id"], "context": c["context"], "description": c["description"]})
        out[r["card"]].append({
            "ref": f"{seg}-{pos}",
            "name": model.field_name(seg, pos),
            "usage": usage,
            "value_sets": sorted(model.bindings(seg, pos)),
            "constraints": cons,
        })
    return out


# ---------------------------------------------------------------- checks: narrative vs model

def check_refs(model: Model, refs: list[dict], f, config: dict) -> None:
    ignore = set(config.get("not_segments", []))
    hl7_segments = set(config.get("hl7_segments", []))
    named = set()
    for r in refs:
        seg, pos = r["segment"], r["field"]
        if seg in ignore:
            continue
        loc = r["statement"]
        if seg not in model.segment_names:
            sev = "warning" if seg in hl7_segments else "note"
            f.add("xml-unknown-segment", "igamt", sev,
                  f"{r['text']} refers to the {seg} segment, which is not in any message profile in the IGAMT export.",
                  card=r["card"], location=loc, key=r["text"], evidence={"text": r["sentence"]})
            continue
        if not model.field_exists(seg, pos):
            n = max(len(s["fields"]) for s in model.flavors_of(seg))
            f.add("xml-unknown-field", "igamt", "issue",
                  f"{r['text']} does not exist: {seg} has {n} fields in the IGAMT export.",
                  card=r["card"], location=loc, key=r["text"], evidence={"text": r["sentence"]})
            continue
        xml_name = model.field_name(seg, pos)
        if r["component"]:
            continue
        for given in (r["name_after"], r["name_before"]):
            if not given or not xml_name or _similar(given, xml_name):
                continue
            key = (r["card"], seg, pos, _norm(given))
            if key in named:
                continue
            named.add(key)
            f.add("xml-field-name", "igamt", "note",
                  f"The text calls {seg}-{pos} \"{given.strip()}\"; its name in the profiles is \"{xml_name}\". "
                  "Using the HL7 name alongside the role name (for example, \"MSH-4 (Sending Facility), the submitting organization\") helps readers match text to the tables.",
                  card=r["card"], location=loc, key=f"{seg}-{pos}|{_norm(given)}",
                  evidence={"text": r["sentence"], "xml": f"{seg}-{pos} {xml_name}"})
        comp = component_hint(r["sentence"])
        bound = model.component_bindings(seg, pos, comp) if comp else model.bindings(seg, pos)
        if not r["codes"] or not bound:
            continue
        known = model.codes(bound)
        nonempty = [v for v in bound if model.value_sets.get(v, {}).get("codes")]
        if not nonempty:
            continue
        for code in r["codes"]:
            if code in known:
                continue
            f.add("xml-code-not-bound", "igamt", "warning",
                  f"The text uses code '{code}' for {seg}-{pos}, but '{code}' is not in the value set{'s' if len(nonempty) > 1 else ''} bound to "
                  f"{seg}-{pos} in the profiles ({', '.join(sorted(nonempty))}).",
                  card=r["card"], location=loc, key=f"{seg}-{pos}|{code}",
                  evidence={"text": r["sentence"], "xml": f"{seg}-{pos} bound to {', '.join(sorted(nonempty))}"})


COMPONENT_HINTS = [(re.compile(r"\bname type\b", re.I), 7), (re.compile(r"\baddress type\b", re.I), 7),
                   (re.compile(r"\bidentifier type\b", re.I), 5)]


def component_hint(sentence: str) -> int | None:
    for rx, comp in COMPONENT_HINTS:
        if rx.search(sentence):
            return comp
    return None


def code_usage_notes(model: Model, refs: list[dict]) -> list[dict]:
    """Confirmed codes: for the report's 'what was verified' list."""
    out = []
    for r in refs:
        comp = component_hint(r["sentence"])
        if r["segment"] not in model.segment_names:
            bound = set()
        else:
            bound = model.component_bindings(r["segment"], r["field"], comp) if comp else model.bindings(r["segment"], r["field"])
        known = model.codes(bound)
        for code in r["codes"]:
            if code in known:
                vs = known[code]
                usage = next((c["usage"] for c in model.value_sets[vs]["codes"] if c["code"] == code), None)
                out.append({"card": r["card"], "ref": f"{r['segment']}-{r['field']}", "code": code, "value_set": vs, "usage": usage})
    return out


# ---------------------------------------------------------------- Figure 20 vs co-constraints

def cocon_presence(table: dict, loinc: str, match: str | None) -> str | None:
    """'R' (required), the row/group usage (O, S, ...) when allowed, or None when absent."""
    best = None
    for row in table.get("rows", []):
        if any(w.get("code") == loinc for w in row["when"]):
            u = "R" if row["usage"] == "R" and (row["min"] or 0) >= 1 else row["usage"]
            best = u if best is None or u == "R" else best
    for g in table.get("groups", []):
        if match and match.lower() not in g["name"].lower():
            continue
        for row in g["rows"]:
            if any(w.get("code") == loinc for w in row["when"]):
                req = g["usage"] == "R" and (g["min"] or 0) >= 1 and row["usage"] == "R"
                u = "R" if req else (g["usage"] if g["usage"] != "R" else row["usage"])
                if best is None or u == "R":
                    best = u
    return best


def figure_matrix(model: Model, spec: dict) -> dict:
    """Compare a transcribed figure with the co-constraint tables. Unconditional tables for a
    profile apply to every Order Segment Group, so they are merged into that profile's cells."""
    tables = defaultdict(list)
    for t in model.coconstraints:
        tables[t["profile"]].extend(t["tables"])
    cols = spec["columns"]
    uncond = defaultdict(list)
    for ref in spec.get("unconditional", []):
        uncond[ref["profile"]].append(tables[ref["profile"]][ref["table"]])
    rank = {"R": 3, "S": 2, "O": 1}
    matrix = []
    for row in spec["rows"]:
        cells = []
        for col in cols:
            fig = str(row.get(col["id"], "-"))
            xml = []
            for ref in col["tables"]:
                tab = tables[ref["profile"]][ref["table"]] if ref["table"] < len(tables[ref["profile"]]) else None
                vals = [cocon_presence(t, row["loinc"], row.get("match")) for t in ([tab] if tab else []) + uncond[ref["profile"]]]
                vals = [v for v in vals if v]
                pres = max(vals, key=lambda v: rank.get(v, 0)) if vals else None
                xml.append({"label": ref["label"], "value": pres or "-"})
            mismatch = []
            for x in xml:
                v = x["value"]
                if fig == "-" and v != "-":
                    mismatch.append(f"{x['label']}: allowed ({v})")
                elif fig == "R" and v != "R":
                    mismatch.append(f"{x['label']}: {'not required (' + v + ')' if v != '-' else 'absent'}")
                elif fig == "O" and v == "-":
                    mismatch.append(f"{x['label']}: absent")
                elif fig == "O" and v == "R":
                    mismatch.append(f"{x['label']}: required")
            cells.append({"column": col["id"], "figure": fig, "xml": xml, "mismatch": mismatch})
        matrix.append({"label": row["label"], "loinc": row["loinc"], "cells": cells})
    return {"columns": [{"id": c["id"], "label": c["label"]} for c in cols], "rows": matrix,
            "card": spec["card"], "figure": spec["figure"]}


def check_figure(matrix: dict, f) -> None:
    labels = {c["id"]: c["label"] for c in matrix["columns"]}
    for row in matrix["rows"]:
        parts = []
        for cell in row["cells"]:
            if cell["mismatch"]:
                parts.append(f"{labels[cell['column']]} (figure: {cell['figure']}): " + "; ".join(cell["mismatch"]))
        if parts:
            f.add("xml-figure-cocon", "igamt", "warning",
                  f"Figure 20 and the IGAMT co-constraint tables disagree for {row['label']} ({row['loinc']}). " + " | ".join(parts) + ".",
                  card=matrix["card"], location=matrix["figure"], key=row["label"])


# ---------------------------------------------------------------- checks: the export itself

def check_export(model: Model, f) -> None:
    cat = "igamt-export"
    # conditional usage with no predicate
    base_missing = []
    for s in sorted(model.segments.values(), key=lambda s: s["label"]):
        for fld in s["fields"]:
            if fld["usage"] == "C" and not any((p.get("target_path") or "").startswith(f"{fld['position']}[") for p in s["predicates"]):
                if "_IZ" in s["label"]:
                    f.add("igamt-c-no-predicate", cat, "warning",
                          f"{s['label']} {s['name']}-{fld['position']} ({fld['name']}) has usage C but no predicate, so its condition is undefined and validators cannot apply it.",
                          location=f"model:{s['label']}-{fld['position']}")
                else:
                    base_missing.append(f"{s['label']}-{fld['position']}")
    for d in sorted(model.datatypes.values(), key=lambda d: d["xml_id"]):
        for i, c in enumerate(d["components"], 1):
            if c["usage"] == "C" and not any((p.get("target_path") or "").startswith(f"{i}[") for p in d["predicates"]):
                (f.add("igamt-c-no-predicate", cat, "warning",
                       f"{d['label']}.{i} ({c['name']}) has usage C but no predicate.", location=f"model:{d['label']}.{i}")
                 if "_IZ" in d["label"] else base_missing.append(f"{d['label']}.{i}"))
    if base_missing:
        f.add("igamt-c-no-predicate-base", cat, "note",
              f"{len(base_missing)} elements in unconstrained base segments and datatypes have usage C without a predicate "
              f"({', '.join(base_missing)}). Most are not used in immunization messages; consider setting them to O or X, or adding the base-standard predicates.",
              key="base")
    # bindings to empty or placeholder value sets
    bound_at = defaultdict(list)
    for s in model.segments.values():
        for fld in s["fields"]:
            for b in fld.get("bindings", []):
                for v in b["value_sets"]:
                    bound_at[v].append(f"{s['label']}-{fld['position']}")
    for d in model.datatypes.values():
        for i, c in enumerate(d["components"], 1):
            for b in c.get("bindings", []):
                for v in b["value_sets"]:
                    bound_at[v].append(f"{d['label']}.{i}")
    for t in model.coconstraints:
        for tab in t["tables"]:
            rows = list(tab["rows"]) + [r for g in tab.get("groups", []) for r in g["rows"]]
            for r in rows:
                for th in r["then"]:
                    for v in th.get("value_sets", []):
                        loinc = next((w.get("code") for w in r["when"] if w.get("code")), "?")
                        bound_at[v].append(f"{t['profile']} OBX-5 for {loinc}")
    placeholders = []
    for vid, where in sorted(bound_at.items()):
        vs = model.value_sets.get(vid)
        where_s = ", ".join(sorted(set(where))[:8]) + (" …" if len(set(where)) > 8 else "")
        if vs is None:
            f.add("igamt-missing-value-set", cat, "issue", f"Value set {vid} is bound ({where_s}) but not defined in the export.",
                  location=f"model:vs:{vid}")
        elif not vs["codes"]:
            ext = "It is marked external" if vs.get("external") else "It"
            nv = " and is excluded from validation" if vs["no_validation"] else ""
            f.add("igamt-empty-value-set", cat, "note",
                  f"Value set {vid} ({vs['name'] or vid}) has no codes in the export, yet it is bound to {where_s}. {ext}{nv}. "
                  "Readers cannot see the allowed values; list the codes, link to the external source, or say that the values are locally defined.",
                  location=f"model:vs:{vid}")
        elif all(c["code"] in ("...", "") for c in vs["codes"]):
            in_cocon = [w for w in where if "OBX-5 for" in w]
            if in_cocon:
                f.add("igamt-placeholder-binding", cat, "warning",
                      f"{', '.join(sorted(set(in_cocon)))} is bound to {vid} ({vs['name']}), a user-defined table that holds only a placeholder ('...') "
                      "and is excluded from validation, so these codes are not checked at all in that profile.",
                      location=f"model:vs:{vid}")
            else:
                placeholders.append(vid)
    if placeholders:
        f.add("igamt-placeholder-value-set", cat, "note",
              f"{len(placeholders)} HL7 user-defined tables are bound but hold only a placeholder code ('...') and are excluded from validation: "
              f"{', '.join(placeholders)}. Most are on segments IIS do not use (PV1, PV2, IN1-IN3, GT1). "
              "Where a field matters to IIS (for example HL70362 Facility in ORC-17 and RXA-11.4, or HL70300/HL70361 in MSH), the guide should say how values are assigned.",
              key="placeholders")
    for vid, vs in sorted(model.value_sets.items()):
        missing = [c["code"] for c in vs["codes"] if not c.get("usage")]
        if missing and vid in bound_at:
            f.add("igamt-code-no-usage", cat, "note",
                  f"In value set {vid}, {len(missing)} code(s) have no usage (R/P/E): {', '.join(missing[:10])}{' …' if len(missing) > 10 else ''}.",
                  location=f"model:vs:{vid}")
    # reused constraint IDs
    by_id = defaultdict(list)
    for c in model.all_constraints:
        by_id[c["id"]].append(c)
    for cid, items in sorted(by_id.items()):
        texts = sorted({" ".join(c["description"].split()) for c in items})
        if len(texts) > 1:
            f.add("igamt-constraint-id-reuse", cat, "note",
                  f"Constraint ID {cid} is used {len(items)} times with {len(texts)} different wordings ({', '.join(sorted({c['context'] for c in items}))}). "
                  "Either the wording should match or the constraints need distinct IDs, so that a requirement can be cited unambiguously.",
                  location=f"model:cs:{cid}", evidence={"variants": texts})
    nostrength = [c["key"] for c in model.all_constraints if not c.get("strength")]
    if nostrength:
        f.add("igamt-constraint-no-strength", cat, "note",
              f"{len(nostrength)} generated date/time format constraints have no strength (SHALL/SHOULD) and use the placeholder text \"Element 'xxx'\": {', '.join(nostrength)}.",
              key="no-strength")
    # co-constraint consistency
    obx2 = defaultdict(lambda: defaultdict(set))
    obx5 = defaultdict(lambda: defaultdict(set))
    usages = Counter()
    for t in model.coconstraints:
        for ti, tab in enumerate(t["tables"]):
            seen = Counter()
            groups = [("", tab["rows"])] + [(g["name"], g["rows"]) for g in tab.get("groups", [])]
            for g in tab.get("groups", []):
                usages[g["usage"]] += 1
            for gname, rows in groups:
                gseen = Counter()
                for r in rows:
                    usages[r["usage"]] += 1
                    loinc = next((w.get("code") for w in r["when"] if w.get("code")), None)
                    if not loinc:
                        continue
                    gseen[loinc] += 1
                    where = f"{t['profile']} table {ti + 1}" + (f" / {gname}" if gname else "")
                    for th in r["then"]:
                        if th["field"] == "OBX-2" and th.get("value"):
                            obx2[loinc][th["value"]].add(where)
                        if th["field"] == "OBX-5":
                            obx5[loinc][",".join(th.get("value_sets", []))].add(where)
                    if not any(th["field"] == "OBX-5" for th in r["then"]):
                        obx5[loinc]["(none)"].add(where)
                for loinc, n in gseen.items():
                    if n > 1:
                        f.add("igamt-cocon-duplicate-row", cat, "warning",
                              f"In the {t['profile']} co-constraints (table {ti + 1}{', group ' + gname if gname else ''}), LOINC {loinc} has {n} rows. "
                              "A repeated row usually means another observation was meant (for example, a missing VIS date).",
                              location=f"model:cocon:{t['profile']}:{ti + 1}:{gname}:{loinc}")
    for loinc, types in sorted(obx2.items()):
        if len(types) > 1:
            f.add("igamt-cocon-type-mismatch", cat, "warning",
                  f"LOINC {loinc} is given different OBX-2 value types in different co-constraint tables: "
                  + "; ".join(f"{k} in {', '.join(sorted(v))}" for k, v in sorted(types.items())) + ".",
                  location=f"model:cocon-type:{loinc}")
    for loinc, sets in sorted(obx5.items()):
        real = {k: v for k, v in sets.items()}
        if len(real) > 1:
            f.add("igamt-cocon-binding-mismatch", cat, "note",
                  f"LOINC {loinc} has different OBX-5 value set bindings in different co-constraint tables: "
                  + "; ".join(f"{k} in {', '.join(sorted(v))}" for k, v in sorted(real.items())) + ".",
                  location=f"model:cocon-vs:{loinc}")
    odd = {u: n for u, n in usages.items() if u not in ("R", "RE", "O", "C", "X")}
    if odd:
        f.add("igamt-cocon-usage", cat, "note",
              "Co-constraint rows and groups use usage code(s) " + ", ".join(f"'{u}' ({n} times)" for u, n in sorted(odd.items()))
              + ", which the guide's usage designations (R, RE, O, C, X) do not define. The guide should define them, or the tables should use defined codes.",
              key="usage")
    # duplicate datatype labels
    labels = defaultdict(list)
    for d in model.datatypes.values():
        labels[d["label"]].append(d)
    for lab, ds in sorted(labels.items()):
        if len(ds) > 1:
            f.add("igamt-datatype-duplicate", cat, "note",
                  f"Datatype {lab} is defined {len(ds)} times: " + "; ".join(f"{d['xml_id']} (HL7 {d['version']}, \"{d['description']}\")" for d in ds)
                  + ". Only one should remain, with the correct description.",
                  location=f"model:dt:{lab}")
    # unreachable flavors
    used = {p["flavor"] for p in model.placements}
    unreachable = sorted(s for s in model.segments if s not in used)
    if unreachable:
        f.add("igamt-unused-flavor", cat, "note",
              f"Segment flavor(s) {', '.join(unreachable)} are defined but not used by any message (the messages use generated co-constraint copies instead). "
              "Pages for these would confuse readers; they can be hidden or removed.", key="unreachable")
    # profile naming
    suffix = [p["code"] for p in model.profiles if re.search(r"\b(QUERY )?PROFILE\b", p["name"])]
    if suffix:
        f.add("igamt-profile-name", cat, "note",
              "Profile names are not consistent: " + ", ".join(f"{p['code']} \"{p['name']}\"" for p in model.profiles if p["code"] in suffix)
              + " end in \"Profile\" or \"Query Profile\"; the others do not. All names are in capitals.",
              key="names")
    # metadata
    src = read_yaml(model.dir / "source.yml", {}) or {}
    if src.get("version") in (None, "null") or "No Date" in str(src.get("date")):
        f.add("igamt-metadata", cat, "note",
              f"The export has no version or date (Version=\"{src.get('version')}\", Date=\"{src.get('date')}\"). "
              "Without them, a reader or validator cannot tell which draft of the structure a page or result reflects.",
              key="metadata")


# ---------------------------------------------------------------- reviewed findings

def reviewed(quality_dir: Path, f, card_ids: set[str]) -> list[dict]:
    items = read_yaml(quality_dir / "igamt-review.yml", []) or []
    for r in items:
        if r.get("card") and r["card"] not in card_ids:
            raise SystemExit(f"igamt-review.yml: {r['id']} names unknown card {r['card']}")
        if r.get("kind") == "confirmed":
            continue
        msg = r["title"].rstrip(".") + ". " + " ".join(r.get("summary", "").split())
        ev = {k: r[k] for k in ("narrative", "xml", "recommendation", "owner", "kind", "comment") if r.get(k)}
        f.items.append({
            "id": r["id"], "rule": "igamt-review", "category": "igamt",
            "severity": r.get("severity", "warning"), "card": r.get("card"),
            "location": r.get("location"), "message": msg.strip(), "evidence": ev,
        })
    return items


# ---------------------------------------------------------------- entry point

def run(cards, model_dir: Path, quality_dir: Path, f, config: dict) -> dict | None:
    if not Model.available(model_dir):
        return None
    model = Model(model_dir)
    refs = collect_refs(cards)
    check_refs(model, refs, f, config)
    spec = read_yaml(quality_dir / "transcriptions" / "fig-20.yml")
    matrix = figure_matrix(model, spec) if spec else None
    if matrix:
        check_figure(matrix, f)
    check_export(model, f)
    review = reviewed(quality_dir, f, {c.id for c in cards})
    xref = field_xref(model, refs)
    n_fields = len({(r["segment"], r["field"]) for r in refs if r["segment"] in model.segment_names})
    return {
        "xref": xref,
        "figure_20": matrix,
        "review": review,
        "codes_confirmed": code_usage_notes(model, refs),
        "stats": {
            "field_mentions": len(refs),
            "fields": n_fields,
            "cards_with_fields": len(xref),
            "statements_with_fields": len({r["statement"] for r in refs if r["statement"]}),
            "profiles": len(model.profiles),
            "constraints": len(model.all_constraints),
            "constraint_ids": len({c["id"] for c in model.all_constraints}),
            "cocon_tables": sum(len(t["tables"]) for t in model.coconstraints),
            "value_sets": len(model.value_sets),
        },
        "profiles": [{"code": p["code"], "title": p["title"], "type": f"{p['message_type']}^{p['event']}" if p.get("event") else p["message_type"]}
                     for p in sorted(model.profiles, key=lambda p: PROFILE_ORDER.index(p["code"]) if p["code"] in PROFILE_ORDER else 99)],
    }
