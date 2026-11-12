#!/usr/bin/env python3
"""Normalize the IGAMT validation export (NIST hl7-v2-schemas XML) into model/.

    python tools/import_igamt.py                 # directory from inputs.json (igamt_xml_dir)
    python tools/import_igamt.py --xml-dir DIR

The XML stays with the maintainers; only the normalized model is committed.
IGAMT stays authoritative for structure: never edit model/ by hand. Changes go
to IGAMT as change requests and come back through a new export.

Writes (deterministic; re-runs are byte-identical):
    model/source.yml         export metadata and file checksums
    model/profiles.json      message profiles with their segment trees
    model/segments.json      segment flavors with fields, bindings, predicates, constraints
    model/datatypes.json     datatype flavors with components, bindings, predicates, constraints
    model/value-sets.json    value sets with codes
    model/coconstraints.json OBX co-constraint tables
    model/slicings.json      segment slicing (e.g., RXA flavors by record type)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guidecards import REPO, write_text, write_yaml  # noqa: E402

MODEL_DIR = REPO / "model"
FILES = ("Profile.xml", "Constraints.xml", "ValueSetBindings.xml", "ValueSets.xml", "CoConstraints.xml", "Slicings.xml")
POS_RE = re.compile(r"^(\d+)\[([^\]]*)\]$")


# ---------------------------------------------------------------- helpers

def num(v: str | None):
    if v is None or v in ("NA", ""):
        return None
    if v == "*":
        return "*"
    try:
        return int(v)
    except ValueError:
        return v


def assertion(e: ET.Element) -> dict:
    """Generic, lossless assertion tree: {op, attrs..., args: [...]}."""
    d = {"op": e.tag}
    for k, v in e.attrib.items():
        d[k[0].lower() + k[1:]] = v
    kids = [assertion(c) for c in e]
    if kids:
        d["args"] = kids
    if (e.text or "").strip() and not kids:
        d["text"] = e.text.strip()
    return d


def assertion_paths(a: dict) -> list[str]:
    out = []
    for k in ("path", "path1", "path2"):
        if k in a:
            out.append(a[k])
    for c in a.get("args", []):
        out.extend(assertion_paths(c))
    return out


def split_path(path: str) -> list[tuple[int, str]]:
    if path in (".", ""):
        return []
    parts = []
    for p in path.split("."):
        m = POS_RE.match(p)
        if not m:
            raise ValueError(f"Unexpected path step {p!r} in {path!r}")
        parts.append((int(m.group(1)), m.group(2)))
    return parts


def profile_code(name: str) -> tuple[str, str]:
    m = re.match(r"^(Z\d+)\s*-\s*(.*)$", name)
    if not m:
        return name, name
    words = m.group(2).title().replace(" A ", " a ").replace(" An ", " an ").replace(" Of ", " of ")
    words = re.sub(r"\b(Vxu|Qbp|Rsp|Ack)\b", lambda x: x.group(1).upper(), words)
    words = words.replace(" With ", " with ").replace(" No ", " No ").replace(" Using ", " Using ")
    return m.group(1), words


# ---------------------------------------------------------------- loader

class Export:
    def __init__(self, xml_dir: Path):
        self.dir = xml_dir
        missing = [f for f in FILES if not (xml_dir / f).exists()]
        if missing:
            raise SystemExit(f"Missing in {xml_dir}: {', '.join(missing)}")
        self.root = {f: ET.parse(xml_dir / f).getroot() for f in FILES}
        self.segments: dict[str, dict] = {}
        self.datatypes: dict[str, dict] = {}
        self.profiles: list[dict] = []
        self.groups: dict[str, dict] = {}
        self.value_sets: dict[str, dict] = {}

    # ---- profile
    def load_profile(self):
        r = self.root["Profile.xml"]
        for d in r.find("Datatypes"):
            comps = []
            for i, c in enumerate(d.findall("Component"), 1):
                comps.append(self._element(c, i))
            self.datatypes[d.get("ID")] = {
                "label": d.get("Label") or d.get("ID"),
                "xml_id": d.get("ID"),
                "name": d.get("Name"),
                "description": d.get("Description"),
                "version": d.get("Version"),
                "components": comps,
                "constraints": [],
                "predicates": [],
                "used_by": [],
            }
        for s in r.find("Segments"):
            fields = [self._element(f, i) for i, f in enumerate(s.findall("Field"), 1)]
            seg = {
                "label": s.get("Label") or s.get("ID"),
                "xml_id": s.get("ID"),
                "name": s.get("Name"),
                "description": s.get("Description"),
                "version": s.get("Version"),
                "fields": fields,
                "constraints": [],
                "predicates": [],
                "used_in": [],
            }
            dm = s.find("DynamicMapping")
            if dm is not None:
                seg["dynamic_mapping"] = [{k[0].lower() + k[1:]: v for k, v in m.attrib.items()} for m in dm]
            self.segments[seg["xml_id"]] = seg
        for m in r.find("Messages"):
            code, title = profile_code(m.get("Name"))
            prof = {
                "id": code.lower(),
                "code": code,
                "igamt_id": m.get("ID"),
                "name": m.get("Name"),
                "title": title,
                "message_type": m.get("Type"),
                "event": m.get("Event"),
                "structure": m.get("StructID"),
                "description": m.get("Description"),
                "children": [self._node(c, code, []) for c in m],
                "constraints": [],
                "predicates": [],
            }
            self.profiles.append(prof)
        order = ["Z22", "Z23", "Z34", "Z44", "Z31", "Z32", "Z33", "Z42"]
        self.profiles.sort(key=lambda p: order.index(p["code"]) if p["code"] in order else 99)

    def _element(self, e: ET.Element, pos: int) -> dict:
        d = {
            "position": pos,
            "name": e.get("Name"),
            "usage": e.get("Usage"),
            "datatype": e.get("Datatype"),
        }
        if e.get("Min") is not None:
            d["min"] = num(e.get("Min"))
            d["max"] = num(e.get("Max"))
        for k, src in (("min_length", "MinLength"), ("max_length", "MaxLength"), ("conf_length", "ConfLength")):
            v = num(e.get(src))
            if v is not None:
                d[k] = v
        return d

    def _node(self, e: ET.Element, code: str, trail: list[str]) -> dict:
        if e.tag == "Segment":
            seg = self.segments[e.get("Ref")]
            seg["used_in"].append({"profile": code, "path": ".".join(trail + [seg["name"]])})
            return {"kind": "segment", "ref": e.get("Ref"), "segment": seg["name"], "usage": e.get("Usage"),
                    "min": num(e.get("Min")), "max": num(e.get("Max"))}
        g = {"kind": "group", "xml_id": e.get("ID"), "name": e.get("Name"), "usage": e.get("Usage"),
             "min": num(e.get("Min")), "max": num(e.get("Max")), "constraints": [], "predicates": []}
        g["children"] = [self._node(c, code, trail + [g["name"]]) for c in e]
        self.groups[g["xml_id"]] = g
        g["_profile"] = code
        return g

    # ---- path resolution (positional XML paths → readable field addresses)
    def resolve(self, ctx_kind: str, ctx, path: str) -> dict:
        """Return {'text': 'ORDER.RXA-20.1', 'segment': 'RXA', 'field': 20, 'component': 1, 'flavor': label}."""
        steps = split_path(path)
        names: list[str] = []
        seg = None
        dt = None
        out: dict = {}
        if ctx_kind in ("message", "group"):
            node = ctx
            while steps:
                pos, _ = steps.pop(0)
                child = node["children"][pos - 1]
                if child["kind"] == "group":
                    names.append(child["name"])
                    node = child
                    continue
                seg = self.segments[child["ref"]]
                names.append(seg["name"])
                break
        elif ctx_kind == "segment":
            seg = ctx
        elif ctx_kind == "datatype":
            dt = ctx
        if seg is not None:
            out["segment"] = seg["name"]
            out["flavor"] = seg["label"]
            if steps:
                pos, _ = steps.pop(0)
                out["field"] = pos
                fld = seg["fields"][pos - 1] if pos - 1 < len(seg["fields"]) else None
                addr = f"{seg['name']}-{pos}"
                if fld:
                    out["field_name"] = fld["name"]
                    dt = self.datatypes.get(fld["datatype"])
                for i, (p, _) in enumerate(steps):
                    addr += f".{p}"
                    if i == 0:
                        out["component"] = p
                if names:
                    names[-1] = addr
                else:
                    names.append(addr)
                return {"text": ".".join(names), **out}
            return {"text": ".".join(names) or seg["name"], **out}
        if dt is not None:
            out["datatype"] = dt["label"]
            addr = dt["name"]
            if steps:
                addr += "." + ".".join(str(p) for p, _ in steps)
                out["component"] = steps[0][0]
            return {"text": addr, **out}
        return {"text": ".".join(names) or path}

    # ---- constraints and predicates
    def load_constraints(self):
        r = self.root["Constraints.xml"]
        for section in ("Constraints", "Predicates"):
            sec = r.find(section)
            if sec is None:
                continue
            for kind in sec:
                for by in kind:
                    cid = by.get("ID")
                    ctx_kind, ctx = self._context(kind.tag, cid)
                    for c in by:
                        a = c.find("Assertion")
                        if a is None:
                            a = c.find("Condition")
                        tree = assertion(a[0]) if a is not None and len(a) else None
                        paths = assertion_paths(tree) if tree else []
                        targets = []
                        for p in dict.fromkeys(paths):
                            try:
                                targets.append(self.resolve(ctx_kind, ctx, p)["text"])
                            except (ValueError, IndexError, KeyError):
                                targets.append(p)
                        item = {
                            "description": " ".join((c.findtext("Description") or "").split()),
                        }
                        if section == "Constraints":
                            item = {"id": c.get("ID"), "strength": c.get("Strength"), **item}
                        else:
                            tgt = c.get("Target")
                            try:
                                item["target"] = self.resolve(ctx_kind, ctx, tgt)["text"]
                            except (ValueError, IndexError, KeyError):
                                item["target"] = tgt
                            item["target_path"] = tgt
                            item["true_usage"] = c.get("TrueUsage")
                            item["false_usage"] = c.get("FalseUsage")
                        item["references"] = targets
                        item["assertion"] = tree
                        ctx[section.lower()].append(item)

    def _context(self, kind: str, cid: str):
        if kind == "Segment":
            return "segment", self.segments[cid]
        if kind == "Datatype":
            return "datatype", self.datatypes[cid]
        if kind == "Group":
            return "group", self.groups[cid]
        if kind == "Message":
            return "message", next(p for p in self.profiles if p["igamt_id"] == cid)
        raise ValueError(kind)

    # ---- bindings
    def load_bindings(self):
        r = self.root["ValueSetBindings.xml"]
        r = r.find("ValueSetBindings") if r.find("ValueSetBindings") is not None else r
        for kind in r:
            for by in kind:
                target = self.segments[by.get("ID")] if kind.tag == "Segment" else self.datatypes[by.get("ID")]
                elems = target["fields"] if kind.tag == "Segment" else target["components"]
                for b in by.findall("ValueSetBinding"):
                    steps = split_path(b.get("Target"))
                    binding = self._binding(b)
                    el = elems[steps[0][0] - 1]
                    if len(steps) > 1:
                        binding["path"] = ".".join(str(p) for p, _ in steps[1:])
                    el.setdefault("bindings", []).append(binding)

    @staticmethod
    def _binding(b: ET.Element) -> dict:
        locs = []
        for loc in b.find("BindingLocations") if b.find("BindingLocations") is not None else []:
            if loc.tag == "SimpleBindingLocation":
                locs.append(loc.get("CodeLocation"))
            else:
                locs.append(f"{loc.get('CodeLocation')}|{loc.get('CodeSystemLocation')}")
        return {
            "value_sets": [x.get("BindingIdentifier") for x in b.iter("Binding")],
            "strength": b.get("BindingStrength"),
            "locations": locs,
        }

    # ---- value sets
    def load_value_sets(self):
        r = self.root["ValueSets.xml"]
        no_val = set()
        nv = r.find("NoValidation")
        if nv is not None:
            no_val = {x.text.strip() for x in nv if x.text}
        for grp in r.findall("ValueSetDefinitions"):
            for v in grp:
                vid = v.get("BindingIdentifier")
                d = {
                    "id": vid,
                    "name": v.get("Name"),
                    "description": v.get("Description"),
                    "group": grp.get("Group"),
                    "content_definition": v.get("ContentDefinition"),
                    "stability": v.get("Stability"),
                    "extensibility": v.get("Extensibility"),
                    "no_validation": vid in no_val,
                }
                if v.get("Version"):
                    d["version"] = v.get("Version")
                if v.tag == "ExternalValueSetDefinition":
                    d["external"] = {k[0].lower() + k[1:]: val for k, val in v.attrib.items()
                                     if k not in ("BindingIdentifier", "Name", "Description")}
                codes = []
                for c in v.findall("ValueElement"):
                    code = {"code": c.get("Value"), "display": c.get("DisplayName"), "system": c.get("CodeSystem"),
                            "usage": c.get("Usage")}
                    if c.get("Comments"):
                        code["comments"] = c.get("Comments")
                    codes.append(code)
                d["codes"] = codes
                self.value_sets[vid] = d

    # ---- co-constraints and slicing
    def load_coconstraints(self) -> list[dict]:
        r = self.root["CoConstraints.xml"]
        out = []
        for bm in r.findall("ByMessage"):
            prof = next(p for p in self.profiles if p["igamt_id"] == bm.get("ID"))
            for ctx in bm.findall("Context"):
                for seg in ctx.findall("Segment"):
                    try:
                        where = self.resolve("message", prof, seg.get("Path"))["text"]
                    except (ValueError, IndexError, KeyError):
                        where = seg.get("Path")
                    tables = []
                    for t in seg:
                        tab = {"kind": "conditional" if t.tag == "ConditionalTable" else "simple"}
                        cond = t.find("Condition")
                        if cond is not None:
                            tab["condition"] = " ".join((cond.findtext("Description") or "").split())
                        gid = t.find("CoConstraintGroupId")
                        if gid is not None:
                            tab["group_by"] = [p.get("Name") for p in gid]
                        rows, groups = [], []
                        for c in t:
                            if c.tag == "CoConstraint":
                                rows.append(self._cc_row(c))
                            elif c.tag == "CoConstraintGroup":
                                g = {"name": c.get("Name"), "usage": c.get("Usage"), "min": num(c.get("Min")),
                                     "max": num(c.get("Max")), "rows": []}
                                for cc in c:
                                    row = self._cc_row(cc)
                                    if cc.tag == "Primary":
                                        row["primary"] = True
                                    g["rows"].append(row)
                                groups.append(g)
                        tab["rows"] = rows
                        if groups:
                            tab["groups"] = groups
                        tables.append(tab)
                    out.append({"profile": prof["code"], "segment": seg.get("Name"), "location": where, "tables": tables})
        return out

    def _cc_row(self, c: ET.Element) -> dict:
        row = {"usage": c.get("Usage"), "min": num(c.get("Min")), "max": num(c.get("Max")), "when": [], "then": []}
        for part, key in (("Selectors", "when"), ("Constraints", "then")):
            sec = c.find(part)
            if sec is None:
                continue
            for x in sec:
                item = {"field": x.get("Name"), "kind": x.tag}
                if x.tag == "Code":
                    item.update(code=x.get("Code"), system=x.get("CodeSystem"))
                elif x.tag == "PlainText":
                    item["value"] = x.get("Value")
                elif x.tag == "ValueSet":
                    b = x.find("ValueSetBinding")
                    item.update(self._binding(b))
                else:
                    item["detail"] = assertion(x)
                row[key].append(item)
        return row

    def load_slicings(self) -> list[dict]:
        r = self.root["Slicings.xml"]
        out = []
        for kind in r:
            for m in kind:
                prof = next(p for p in self.profiles if p["igamt_id"] == m.get("ID"))
                for gc in m:
                    ctx = prof if gc.get("ID") == prof["igamt_id"] else self.groups[gc.get("ID")]
                    for sl in gc:
                        pos = int(sl.get("Position"))
                        child = ctx["children"][pos - 1]
                        slices = []
                        for s in sl:
                            a = s.find("Assertion")
                            slices.append({
                                "flavor": s.get("Ref"),
                                "when": " ".join((s.findtext("Description") or "").split()),
                                "assertion": assertion(a[0]) if a is not None and len(a) else None,
                            })
                        out.append({
                            "profile": prof["code"],
                            "context": ctx.get("name") or prof["structure"],
                            "segment": child.get("segment"),
                            "default_flavor": child.get("ref"),
                            "kind": sl.tag,
                            "slices": slices,
                        })
        return out


# ---------------------------------------------------------------- output

def strip_private(obj):
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


def dump(path: Path, data) -> None:
    write_text(path, json.dumps(strip_private(data), indent=1, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xml-dir", type=Path, help="IGAMT export directory (default: igamt_xml_dir in inputs.json)")
    args = ap.parse_args()
    xml_dir = args.xml_dir
    if xml_dir is None:
        inputs = REPO / "inputs.json"
        if not inputs.exists():
            ap.error("No --xml-dir given and no inputs.json (copy inputs.example.json).")
        xml_dir = Path(json.loads(inputs.read_text(encoding="utf-8"))["igamt_xml_dir"])

    ex = Export(xml_dir)
    ex.load_profile()
    ex.load_constraints()
    ex.load_bindings()
    ex.load_value_sets()
    cocon = ex.load_coconstraints()
    slicing = ex.load_slicings()

    # which datatypes are used by which segment/datatype flavors
    for s in ex.segments.values():
        for f in s["fields"]:
            dt = ex.datatypes.get(f["datatype"])
            if dt is not None and s["label"] not in dt["used_by"]:
                dt["used_by"].append(s["label"])
    for d in list(ex.datatypes.values()):
        for c in d["components"]:
            dt = ex.datatypes.get(c["datatype"])
            if dt is not None and d["label"] not in dt["used_by"]:
                dt["used_by"].append(d["label"])

    meta = ex.root["Profile.xml"].find("MetaData").attrib
    MODEL_DIR.mkdir(exist_ok=True)
    write_yaml(MODEL_DIR / "source.yml", {
        "format": "NIST hl7-v2-schemas validation export",
        "export": xml_dir.name,
        "schema_version": re.search(r"hl7-v2-schemas/([\d.]+)/",
                                    ex.root["Profile.xml"].get("{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation", "")
                                    ).group(1),
        "name": meta.get("Name"),
        "organization": meta.get("OrgName"),
        "version": meta.get("Version"),
        "date": meta.get("Date"),
        "files": {f: hashlib.sha256((xml_dir / f).read_bytes()).hexdigest()[:16] for f in FILES},
    }, header="Generated by tools/import_igamt.py. Do not edit.")
    dump(MODEL_DIR / "profiles.json", ex.profiles)
    dump(MODEL_DIR / "segments.json", sorted(ex.segments.values(), key=lambda s: s["label"]))
    dump(MODEL_DIR / "datatypes.json", sorted(ex.datatypes.values(), key=lambda d: (d["label"], d["xml_id"])))
    dump(MODEL_DIR / "value-sets.json", sorted(ex.value_sets.values(), key=lambda v: v["id"].lower()))
    dump(MODEL_DIR / "coconstraints.json", cocon)
    dump(MODEL_DIR / "slicings.json", slicing)

    n_con = sum(len(x["constraints"]) for x in [*ex.segments.values(), *ex.datatypes.values(), *ex.groups.values(), *ex.profiles])
    n_pred = sum(len(x["predicates"]) for x in [*ex.segments.values(), *ex.datatypes.values(), *ex.groups.values(), *ex.profiles])
    print(f"{len(ex.profiles)} profiles, {len(ex.segments)} segment flavors, {len(ex.datatypes)} datatypes, "
          f"{len(ex.value_sets)} value sets, {n_con} constraints, {n_pred} predicates, "
          f"{sum(len(t['tables']) for t in cocon)} co-constraint tables, {len(slicing)} slicings -> model/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
