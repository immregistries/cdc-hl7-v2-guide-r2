#!/usr/bin/env python3
"""Structural comparison of this guide's profiles (model/) with the Release 1.5 baseline (prior/release-1.5/model/).

    python tools/diff_r15.py          # writes output/r15/changes.csv and output/r15/summary.md

The baseline for format and validation is NIST's conformance profiles for Release 1.5 (see
prior/release-1.5/README.md). Both models come from NIST hl7-v2-schemas exports, so they are compared element by
element:

- segments in each message profile (groups matched by their first segment, since the two exports name them
  differently): added, removed, usage, cardinality
- fields and components (two levels): usage, cardinality, data type, length, value set bindings
- codes in the value sets bound to each element, except for externally maintained code systems (CVX, MVX, NDC, ...;
  quality/r15/config.yml), which change all the time and are reported only as a binding

A change that is the same in several profiles (MSH-19 in all eight, say) is one row with the list of profiles.
compute() is used by the site builder; this script is for looking at the result on its own.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guidecards import REPO, read_yaml, write_text  # noqa: E402

PRIOR_MODEL = REPO / "prior" / "release-1.5" / "model"
CONFIG = REPO / "quality" / "r15" / "config.yml"
PROFILE_ORDER = ["Z22", "Z23", "Z34", "Z44", "Z31", "Z32", "Z33", "Z42"]
USAGE_RANK = {"X": 0, "O": 1, "C": 2, "RE": 3, "R": 4}  # for "tightened"/"loosened"
ASPECTS = ["segment", "element", "usage", "cardinality", "datatype", "length", "binding", "codes"]
ASPECT_LABEL = {
    "segment": "Segment", "element": "Element", "usage": "Usage", "cardinality": "Cardinality",
    "datatype": "Data type", "length": "Length", "binding": "Value set", "codes": "Codes",
}


# ---------------------------------------------------------------- loading

class Model:
    def __init__(self, folder: Path):
        rd = lambda n: json.loads((folder / n).read_text(encoding="utf-8"))  # noqa: E731
        self.profiles = {p["code"]: p for p in rd("profiles.json")}
        self.segments = {s["xml_id"]: s for s in rd("segments.json")}
        self.datatypes = {d["xml_id"]: d for d in rd("datatypes.json")}
        self.value_sets = {v["id"]: v for v in rd("value-sets.json")}

    def segment_rows(self, code: str) -> dict[str, dict]:
        """{key: {path, usage, min, max, ref}} for every segment in the profile, keyed by its group anchors."""
        out: dict[str, dict] = {}

        def anchor(group) -> str:
            for c in group["children"]:
                return c["segment"] if c["kind"] == "segment" else anchor(c)
            return group["name"]

        def walk(nodes, keys, names, gusage):
            for n in nodes:
                if n["kind"] == "segment":
                    key = "/".join(keys + [n["segment"]])
                    out[key] = {"path": "/".join(names + [n["segment"]]), "segment": n["segment"], "ref": n["ref"],
                                "usage": n["usage"], "min": n["min"], "max": n["max"], "in_x_group": gusage == "X"}
                else:
                    # A group that only wraps another group (Z31 RESPONSE in Release 1.5) is the same as that group.
                    g = n
                    while len(g["children"]) == 1 and g["children"][0]["kind"] != "segment":
                        inner = g["children"][0]
                        mx = "*" if "*" in (g["max"], inner["max"]) else g["max"] * inner["max"]
                        g = {**inner, "usage": g["usage"] if USAGE_RANK.get(g["usage"], 0) < USAGE_RANK.get(inner["usage"], 0)
                             else inner["usage"], "min": g["min"] * inner["min"], "max": mx}
                    walk(g["children"], keys + [f"[{anchor(g)}]"], names + [g["name"]], "X" if g["usage"] == "X" else gusage)
                    out["/".join(keys + [f"[{anchor(g)}]"])] = {"path": "/".join(names + [g["name"]]), "group": True,
                                                               "usage": g["usage"], "min": g["min"], "max": g["max"]}

        walk(self.profiles[code]["children"], [], [], None)
        return out


def card(e) -> str:
    return f"[{e.get('min')}..{e.get('max')}]"


def length(e):
    lo, hi = e.get("min_length"), e.get("max_length")
    if hi is None:
        return None
    return f"{lo}..{hi}" if lo not in (None, 1) else str(hi)


def base_dt(dt: str | None) -> str:
    return (dt or "").split("_")[0]


# ---------------------------------------------------------------- value sets

class ValueSets:
    """Matches value sets across the two models by what they contain, not by ID (the exports name them differently)."""

    def __init__(self, model: Model, external: set[str]):
        self.m = model
        self.external = external

    def systems(self, vs_id: str) -> list[str]:
        vs = self.m.value_sets.get(vs_id)
        if not vs:
            return []
        return sorted({c.get("system") or "" for c in vs.get("codes", [])} - {""})

    def key(self, vs_id: str) -> str:
        sys_ = self.systems(vs_id)
        if len(sys_) == 1:
            return sys_[0]
        return re.sub(r"(_IZ\d*|_IIS|_\d+|_Active|_Inactive|_Non-US)$", "", vs_id, flags=re.I)

    def is_external(self, vs_id: str) -> bool:
        s = set(self.systems(vs_id)) or {self.key(vs_id)}
        return bool(s) and s <= self.external

    def codes(self, vs_ids) -> dict[tuple[str, str], str]:
        out = {}
        for v in vs_ids:
            for c in (self.m.value_sets.get(v) or {}).get("codes", []):
                if c["code"] == "...":  # NIST's placeholder for "no suggested values"
                    continue
                # by code alone: the two exports name some code systems differently (CDCREC, PHVS_...)
                # a code allowed by any of the bound sets is allowed
                if c.get("usage") != "E" or c["code"] not in out:
                    out[c["code"]] = "E" if c.get("usage") == "E" else "P"
        return out


def bindings(el) -> list[str]:
    return sorted({v for b in el.get("bindings", []) for v in b["value_sets"]})


# ---------------------------------------------------------------- comparison

def compute(repo: Path = REPO) -> dict:
    cfg = read_yaml(repo / "quality" / "r15" / "config.yml", {}) or {}
    external = set(cfg.get("external_code_systems", []))
    old, new = Model(repo / "prior" / "release-1.5" / "model"), Model(repo / "model")
    vso, vsn = ValueSets(old, external), ValueSets(new, external)
    rows: dict[tuple, dict] = {}
    length_dropped: dict[tuple, set] = defaultdict(set)
    code_changes: dict[tuple, dict] = {}

    def add(profile, element, name, aspect, before, after, note="", path=""):
        k = (element, aspect, str(before), str(after), note)
        r = rows.setdefault(k, {"element": element, "name": name, "aspect": aspect, "old": before, "new": after,
                                "note": note, "profiles": [], "paths": set()})
        if profile not in r["profiles"]:
            r["profiles"].append(profile)
        if path:
            r["paths"].add(path)

    def compare_el(profile, path, label, name, eo, en, depth):
        if eo.get("usage") != en.get("usage"):
            add(profile, label, name, "usage", eo.get("usage"), en.get("usage"), path=path)
        if (eo.get("min"), eo.get("max")) != (en.get("min"), en.get("max")) and "min" in eo:
            add(profile, label, name, "cardinality", card(eo), card(en), path=path)
        if base_dt(eo.get("datatype")) != base_dt(en.get("datatype")):
            add(profile, label, name, "datatype", base_dt(eo.get("datatype")), base_dt(en.get("datatype")), path=path)
        lo, ln = length(eo), length(en)
        if lo != ln:
            if ln is None:
                length_dropped[(label, name)].add(profile)
            else:
                add(profile, label, name, "length", lo or "-", ln, path=path)
        constrained = not ({eo.get("usage"), en.get("usage")} <= {"O", "X"})
        bo, bn = (bindings(eo), bindings(en)) if constrained else ([], [])
        ko = {vso.key(v) for v in bo}
        kn = {vsn.key(v) for v in bn}
        if ko != kn:
            add(profile, label, name, "binding", ", ".join(sorted(ko)) or "-", ", ".join(sorted(kn)) or "-", path=path)
        internal_o = [v for v in bo if not vso.is_external(v)]
        internal_n = [v for v in bn if not vsn.is_external(v)]
        co, cn = (vso.codes(internal_o), vsn.codes(internal_n)) if internal_o and internal_n else ({}, {})
        # A value set that lists no codes is defined elsewhere (PHIN VADS, say): nothing to compare.
        # R (required) and P (permitted) both mean "allowed"; the two exports use them differently, so only a change
        # between allowed and excluded (E) counts. Reported once per change, with the elements it affects.
        if co and cn:
            added = tuple(sorted(c for c in cn if c not in co and cn[c] != "E"))
            removed = tuple(sorted(c for c in co if co[c] != "E" and (c not in cn or cn[c] == "E")))
            if added or removed:
                vs = code_changes.setdefault((", ".join(sorted(kn)), added, removed),
                                             {"value_set": ", ".join(sorted(kn)), "added": list(added),
                                              "removed": list(removed), "elements": {}})
                vs["elements"].setdefault(label, set()).add(profile)
        # Components only where a guide constrains the element: not for O or X elements in both.
        if depth < 2 and constrained:
            dto, dtn = old.datatypes.get(eo.get("datatype")), new.datatypes.get(en.get("datatype"))
            if dto and dtn and base_dt(dto["xml_id"]) == base_dt(dtn["xml_id"]):
                compare_children(profile, path, label, dto["components"], dtn["components"], depth + 1)

    def compare_children(profile, path, label, co, cn, depth):
        sep = "-" if depth == 1 else "."
        no = {c["position"]: c for c in co}
        nn = {c["position"]: c for c in cn}
        for pos in sorted(set(no) | set(nn)):
            lab = f"{label}{sep}{pos}"
            a, b = no.get(pos), nn.get(pos)
            if a is None:
                add(profile, lab, b["name"], "element", "-", f"added ({b['usage']})", path=path)
            elif b is None:
                add(profile, lab, a["name"], "element", f"{a['usage']}", "removed", path=path)
            elif a["usage"] == "X" and b["usage"] == "X":
                continue
            else:
                compare_el(profile, path, lab, b["name"], a, b, depth)

    for code in PROFILE_ORDER:
        if code not in old.profiles or code not in new.profiles:
            continue
        so, sn = old.segment_rows(code), new.segment_rows(code)
        for key in sorted(set(so) | set(sn), key=lambda k: (k.count("/"), k)):
            a, b = so.get(key), sn.get(key)
            label = (b or a)["path"]
            what = "group" if (b or a).get("group") else ""
            if a is None:
                if b.get("in_x_group"):
                    continue
                if b["usage"] == "X":
                    add(code, label, what, "segment", "-", "added, not supported (X)")
                else:
                    add(code, label, what, "segment", "-", f"added {b['usage']} {card(b)}")
                continue
            if b is None:
                add(code, label, what, "segment", f"{a['usage']} {card(a)}", "removed")
                continue
            if (a["usage"], a["min"], a["max"]) != (b["usage"], b["min"], b["max"]):
                add(code, label, what, "segment", f"{a['usage']} {card(a)}", f"{b['usage']} {card(b)}")
            if a.get("group") or b["usage"] == "X":
                continue
            seg_o, seg_n = old.segments[a["ref"]], new.segments[b["ref"]]
            compare_children(code, label, b["segment"], seg_o["fields"], seg_n["fields"], 1)

    out = sorted(rows.values(), key=lambda r: (_el_sort(r["element"]), ASPECTS.index(r["aspect"]), str(r["old"])))
    for r in out:
        r["profiles"].sort(key=PROFILE_ORDER.index)
        r["paths"] = sorted(r["paths"])
        r["kind"] = _kind(r)
    return {
        "rows": out,
        "length_dropped": sorted(((el, name, sorted(p, key=PROFILE_ORDER.index)) for (el, name), p in length_dropped.items()),
                                 key=lambda x: _el_sort(x[0])),
        "code_changes": sorted(({**c, "elements": [(el, sorted(p, key=PROFILE_ORDER.index))
                                                    for el, p in sorted(c["elements"].items(), key=lambda x: _el_sort(x[0]))]}
                                for c in code_changes.values()), key=lambda c: (c["value_set"], -len(c["elements"]))),
        "external": sorted(external),
        "counts": Counter(r["aspect"] for r in out),
    }


def _el_sort(label: str):
    m = re.match(r"^([A-Z0-9]{3})(?:-(\d+))?(?:\.(\d+))?(?:\.(\d+))?$", label)
    if m:
        return (0, m.group(1), *(int(x) if x else 0 for x in m.groups()[1:]))
    return (1, label, 0, 0, 0)


def _kind(r) -> str:
    """tightened / loosened / changed, for usage and cardinality (what an implementer most needs to know)."""
    if r["aspect"] == "usage" and r["old"] in USAGE_RANK and r["new"] in USAGE_RANK:
        d = USAGE_RANK[r["new"]] - USAGE_RANK[r["old"]]
        return "tightened" if d > 0 else "loosened" if d < 0 else "changed"
    if r["aspect"] == "segment" and r["new"] == "removed" or r["aspect"] == "element" and r["new"] == "removed":
        return "removed"
    if r["aspect"] in ("segment", "element") and str(r["old"]) == "-":
        return "added"
    return "changed"


# ---------------------------------------------------------------- output

def to_csv(result: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Element", "Name", "Aspect", "Release 1.5 (NIST)", "This guide", "Change", "Profiles", "Note", "Where"])
    for r in result["rows"]:
        w.writerow([r["element"], r["name"], ASPECT_LABEL[r["aspect"]], r["old"], r["new"], r["kind"],
                    " ".join(r["profiles"]), r["note"], "; ".join(r["paths"])])
    for el, name, profiles in result["length_dropped"]:
        w.writerow([el, name, "Length", "(set)", "(not set)", "changed", " ".join(profiles), "length not stated", ""])
    for c in result["code_changes"]:
        for el, profiles in c["elements"]:
            w.writerow([el, "", "Codes", "removed: " + ", ".join(c["removed"]) if c["removed"] else "-",
                        "added: " + ", ".join(c["added"]) if c["added"] else "-", "changed", " ".join(profiles),
                        c["value_set"], ""])
    return buf.getvalue()


def main() -> int:
    res = compute()
    out = REPO / "output" / "r15"
    write_text(out / "changes.csv", to_csv(res))
    lines = ["# Structural changes from Release 1.5 (NIST profiles)", ""]
    lines += [f"- {ASPECT_LABEL[a]}: {res['counts'].get(a, 0)}" for a in ASPECTS]
    lines += [f"- Lengths no longer stated: {len(res['length_dropped'])} elements", "",
              f"External code systems (codes not compared): {', '.join(res['external'])}", ""]
    for r in res["rows"]:
        lines.append(f"- `{r['element']}` {r['name']} · {ASPECT_LABEL[r['aspect']]}: {r['old']} → {r['new']}"
                     f"{' (' + r['note'] + ')' if r['note'] else ''} · {' '.join(r['profiles'])}")
    lines += ["", "## Codes", ""]
    for c in res["code_changes"]:
        lines.append(f"- {c['value_set']}: added {', '.join(c['added']) or '-'}; removed {', '.join(c['removed']) or '-'}"
                     f" · {', '.join(el for el, _ in c['elements'])}")
    write_text(out / "summary.md", "\n".join(lines) + "\n")
    print(", ".join(f"{ASPECT_LABEL[a]} {res['counts'].get(a, 0)}" for a in ASPECTS)
          + f"; lengths dropped {len(res['length_dropped'])} -> output/r15/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
