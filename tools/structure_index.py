"""Read-only index over model/ (the normalized IGAMT export) for cross-checks and pages.

Answers questions such as "what does the XML say about RXA-20 in each profile?":
usage, cardinality, datatype, bound value sets and codes, predicates, and the
conformance statements that reference the field.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import cached_property
from pathlib import Path

FIELD_RE = re.compile(r"\b([A-Z][A-Z0-9]{2})-(\d{1,2})((?:\.\d{1,2}){0,2})\b")
REF_RE = re.compile(r"(?:^|\.)([A-Z][A-Z0-9]{2})-(\d{1,2})((?:\.\d{1,2}){0,2})$")
PROFILE_ORDER = ["Z22", "Z23", "Z34", "Z44", "Z31", "Z32", "Z33", "Z42"]


def parse_ref(text: str):
    """'ORDER.RXA-20.1' → ('RXA', 20, 1)."""
    m = REF_RE.search(text)
    if not m:
        return None
    comp = m.group(3).split(".")[1] if m.group(3) else None
    return m.group(1), int(m.group(2)), int(comp) if comp else None


class Model:
    def __init__(self, model_dir: Path):
        self.dir = model_dir
        load = lambda n: json.loads((model_dir / n).read_text(encoding="utf-8"))  # noqa: E731
        self.profiles = load("profiles.json")
        self.segments = {s["xml_id"]: s for s in load("segments.json")}
        self.datatypes = {d["xml_id"]: d for d in load("datatypes.json")}
        self.value_sets = {v["id"]: v for v in load("value-sets.json")}
        self.coconstraints = load("coconstraints.json")
        self.slicings = load("slicings.json")

    @staticmethod
    def available(model_dir: Path) -> bool:
        return (model_dir / "profiles.json").exists()

    # ------------------------------------------------------------ profile → segment flavors
    @cached_property
    def placements(self) -> list[dict]:
        """Every place a segment flavor can occur: profile, group path, usage, cardinality, and
        (for slices) the condition under which the flavor applies."""
        out = []

        def walk(prof, nodes, trail, inherited):
            for n in nodes:
                if n["kind"] == "group":
                    walk(prof, n["children"], trail + [n["name"]], inherited or n["usage"] == "X")
                    continue
                base = {"profile": prof["code"], "path": ".".join(trail + [n["segment"]]), "segment": n["segment"],
                        "usage": n["usage"], "min": n["min"], "max": n["max"], "excluded": inherited or n["usage"] == "X"}
                slices = [s for s in self.slicings if s["profile"] == prof["code"] and s["default_flavor"] == n["ref"]]
                out.append({**base, "flavor": n["ref"], "slice": None})
                for s in slices:
                    for sl in s["slices"]:
                        out.append({**base, "flavor": sl["flavor"], "slice": sl["when"]})

        for p in self.profiles:
            walk(p, p["children"], [], False)
        return out

    def flavors_of(self, segment: str) -> list[dict]:
        return [s for s in self.segments.values() if s["name"] == segment]

    @cached_property
    def segment_names(self) -> set[str]:
        return {s["name"] for s in self.segments.values()}

    # ------------------------------------------------------------ constraints
    @cached_property
    def all_constraints(self) -> list[dict]:
        """Every conformance statement with its context and a composite key that is unique."""
        out = []

        def add(kind, label, items, profile=None):
            for c in items:
                out.append({**c, "context_kind": kind, "context": label, "profile": profile,
                            "key": f"{label}--{c['id']}"})

        for p in self.profiles:
            add("message", p["code"], p["constraints"], p["code"])

            def groups(nodes, trail):
                for n in nodes:
                    if n["kind"] == "group":
                        add("group", f"{p['code']}.{'.'.join(trail + [n['name']])}", n["constraints"], p["code"])
                        groups(n["children"], trail + [n["name"]])
            groups(p["children"], [])
        for s in self.segments.values():
            add("segment", s["label"], s["constraints"])
        for d in self.datatypes.values():
            add("datatype", d["label"], d["constraints"])
        return out

    @cached_property
    def all_predicates(self) -> list[dict]:
        out = []
        for p in self.profiles:
            def groups(nodes, trail):
                for n in nodes:
                    if n["kind"] == "group":
                        for x in n["predicates"]:
                            out.append({**x, "context_kind": "group", "context": f"{p['code']}.{'.'.join(trail + [n['name']])}"})
                        groups(n["children"], trail + [n["name"]])
            groups(p["children"], [])
        for s in self.segments.values():
            for x in s["predicates"]:
                out.append({**x, "context_kind": "segment", "context": s["label"]})
        for d in self.datatypes.values():
            for x in d["predicates"]:
                out.append({**x, "context_kind": "datatype", "context": d["label"]})
        return out

    @cached_property
    def constraints_by_field(self) -> dict[tuple, list[dict]]:
        idx = defaultdict(list)
        for c in self.all_constraints:
            seen = set()
            refs = list(c.get("references") or [])
            for m in FIELD_RE.finditer(c.get("description") or ""):
                refs.append(m.group(0))
            for r in refs:
                pr = parse_ref(r)
                if pr and pr[:2] not in seen:
                    seen.add(pr[:2])
                    idx[pr[:2]].append(c)
        return idx

    # ------------------------------------------------------------ fields
    def field_facts(self, segment: str, position: int) -> list[dict]:
        """One row per placement of a flavor of this segment: profile, path, slice, and the field definition."""
        rows = []
        for pl in self.placements:
            if pl["segment"] != segment:
                continue
            seg = self.segments[pl["flavor"]]
            if position > len(seg["fields"]):
                continue
            fld = seg["fields"][position - 1]
            preds = [p for p in seg["predicates"] if re.match(rf"^{position}\[", p.get("target_path") or "")]
            rows.append({**pl, "field": fld, "predicates": preds})
        return rows

    def field_name(self, segment: str, position: int) -> str | None:
        names = {s["fields"][position - 1]["name"] for s in self.flavors_of(segment) if position <= len(s["fields"])}
        return sorted(names)[0] if names else None

    def field_exists(self, segment: str, position: int) -> bool:
        return any(position <= len(s["fields"]) for s in self.flavors_of(segment))

    def bindings(self, segment: str, position: int) -> set[str]:
        """Value set IDs that govern the *code* of a field in any flavor: bindings on the field
        itself (whole field or its first component) and on the first component of its datatype.
        Bindings on other components (assigning authority, coding system name, ...) are left out."""
        out = set()
        for seg in self.flavors_of(segment):
            if position > len(seg["fields"]):
                continue
            fld = seg["fields"][position - 1]
            for b in fld.get("bindings", []):
                if b.get("path") in (None, "1"):
                    out.update(b["value_sets"])
            dt = self.datatypes.get(fld["datatype"])
            if dt and dt["components"]:
                for b in dt["components"][0].get("bindings", []):
                    out.update(b["value_sets"])
        return out

    def component_bindings(self, segment: str, position: int, component: int) -> set[str]:
        """Value set IDs bound to one component of a field (field-level path or datatype component)."""
        out = set()
        for seg in self.flavors_of(segment):
            if position > len(seg["fields"]):
                continue
            fld = seg["fields"][position - 1]
            for b in fld.get("bindings", []):
                if b.get("path") == str(component):
                    out.update(b["value_sets"])
            dt = self.datatypes.get(fld["datatype"])
            if dt and component <= len(dt["components"]):
                for b in dt["components"][component - 1].get("bindings", []):
                    out.update(b["value_sets"])
        return out

    def codes(self, value_set_ids) -> dict[str, str]:
        out = {}
        for vid in value_set_ids:
            vs = self.value_sets.get(vid)
            if vs:
                for c in vs["codes"]:
                    out.setdefault(c["code"], vid)
        return out

    def find_value_sets(self, name: str) -> list[dict]:
        key = name.lower().replace("_", "").replace("-", "")
        hits = []
        for v in self.value_sets.values():
            vid = v["id"].lower().replace("_", "").replace("-", "")
            if vid == key or vid.startswith(key) or key in vid.replace("iz01", "").replace("iz", ""):
                hits.append(v)
            elif v["codes"] and any((c.get("system") or "").lower() == name.lower() for c in v["codes"][:1]):
                hits.append(v)
        return hits

    def usage_summary(self, segment: str, position: int, include_excluded: bool = False) -> list[tuple[str, str]]:
        """[(label, 'R [1..1]'), ...] grouped by identical definitions."""
        groups: dict[str, list[str]] = defaultdict(list)
        for r in self.field_facts(segment, position):
            if r["excluded"] and not include_excluded:
                continue
            f = r["field"]
            card = f"[{f.get('min')}..{f.get('max')}]"
            u = f["usage"]
            if r["predicates"]:
                p = r["predicates"][0]
                u = f"C({p['true_usage']}/{p['false_usage']})"
            label = f"{r['profile']} {r['flavor']}" + (" (slice)" if r["slice"] else "")
            groups[f"{u} {card} {f['datatype']}"].append(label)
        return sorted(((", ".join(v), k) for k, v in groups.items()), key=lambda kv: kv[0])
