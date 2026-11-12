"""Check the example messages against the IGAMT profiles in model/ (called from check_cards.py).

A small, transparent validator for the parts of the profiles that matter most to readers:

- the profile (MSH-21) and message type (MSH-9);
- segments that the profile does not include or does not support (X), and required segments;
- per segment, the flavor that applies (including the Z22 PID and RXA slices): required (R) fields
  and components that are empty, unsupported (X) ones that are valued, conditional usage evaluated
  from the predicates, and too many repetitions;
- codes in elements bound (strength R) to a value set that lists its codes;
- date/time formats (the DTM flavors) and the other data type and segment conformance statements;
- OBX co-constraints: whether each observation is allowed in its Order Segment Group, with the right
  OBX-2 value type and OBX-5 value set, and whether required observations are present.

Message-level and group-level conformance statements are not evaluated yet. Assertions the evaluator
does not know are skipped, never reported as failures. This does not replace the NIST validator.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import hl7msg
from guidecards import read_yaml
from structure_index import Model

CATEGORY = {"examples": "Example messages"}
STEP_RE = re.compile(r"^(\d+)\[([^\]]*)\]$")
NEEDS_INPUT = ("Question", "Need help", "Not sure what was envisioned")


# ---------------------------------------------------------------- values at a path

def split_level(value: str, level: int) -> list[str]:
    sep = {0: "|", 1: "^", 2: "&"}[level]
    return value.split(sep)


def element_values(value: str, level: int, path: str) -> list[str]:
    """Values at a NIST path relative to an element. level 0 = segment, 1 = field repetition
    (components separated by ^), 2 = component (subcomponents separated by &)."""
    if path in (".", ""):
        return [value] if value.strip() else []
    vals = [(value, level)]
    for step in path.split("."):
        m = STEP_RE.match(step)
        if not m:
            return []
        pos, occ = int(m.group(1)), m.group(2)
        nxt = []
        for v, lv in vals:
            if lv == 0:  # segment → field repetitions
                reps = hl7msg.repetitions(v, pos)
                chosen = reps if occ == "*" else ([reps[int(occ) - 1]] if occ.isdigit() and int(occ) <= len(reps) else [])
                nxt += [(r, 1) for r in chosen]
            elif lv in (1, 2):
                parts = split_level(v, lv)
                if pos <= len(parts):
                    nxt.append((parts[pos - 1], lv + 1))
            else:
                return []
        vals = nxt
    return [v for v, _ in vals if v.strip()]


# ---------------------------------------------------------------- assertions (three-valued: True, False, None = unknown)

class Evaluator:
    def __init__(self, model: Model):
        self.m = model

    def run(self, a: dict | None, value: str, level: int, resolve=None):
        if not a:
            return None
        op = a["op"]
        args = a.get("args", [])
        if op == "AND":
            rs = [self.run(x, value, level, resolve) for x in args]
            return False if False in rs else (None if None in rs else True)
        if op == "OR":
            rs = [self.run(x, value, level, resolve) for x in args]
            return True if True in rs else (None if None in rs else False)
        if op == "NOT":
            r = self.run(args[0], value, level, resolve) if args else None
            return None if r is None else not r
        if op == "IMPLY":
            if len(args) != 2:
                return None
            p = self.run(args[0], value, level, resolve)
            if p is False:
                return True
            q = self.run(args[1], value, level, resolve)
            return q if p is True else (True if q is True else None)
        if op == "XOR":
            rs = [self.run(x, value, level, resolve) for x in args]
            return None if None in rs else (sum(rs) == 1)
        get = (lambda p: resolve(p)) if resolve else (lambda p: element_values(value, level, p))
        if op == "Presence":
            return bool(get(a["path"]))
        if op in ("PlainText", "StringList", "Format", "ValueSet"):
            vals = get(a["path"])
            if not vals:
                npb = (a.get("notPresentBehavior") or "PASS").upper()
                return True if npb == "PASS" else (False if npb == "FAIL" else None)
            ic = (a.get("ignoreCase") or "false") == "true"
            norm = (lambda s: s.lower()) if ic else (lambda s: s)
            if op == "PlainText":
                test = lambda v: norm(v) == norm(a.get("text", ""))  # noqa: E731
            elif op == "StringList":
                allowed = {norm(x.strip()) for x in (a.get("cSV") or "").split(",")}
                test = lambda v: norm(v) in allowed  # noqa: E731
            elif op == "Format":
                rx = re.compile(a.get("regex", ""))
                test = lambda v: bool(rx.search(v))  # noqa: E731
            else:
                vs = self.m.value_sets.get(a.get("valueSetID"))
                if not vs or not vs["codes"] or vs["no_validation"]:
                    return None
                codes = {c["code"] for c in vs["codes"] if c.get("usage") != "E"}
                test = lambda v: v.split("^")[0] in codes  # noqa: E731
            res = [test(v) for v in vals]
            return any(res) if (a.get("atLeastOnce") or "false") == "true" else all(res)
        if op == "PathValue":
            v1, v2 = get(a["path1"]), get(a["path2"])
            if not v1 or not v2:
                npb = (a.get("notPresentBehavior") or "PASS").upper()
                return True if npb == "PASS" else (False if npb == "FAIL" else None)
            if a.get("operator") == "EQ":
                return v1[0] == v2[0]
            return None
        return None  # SetID, Plugin, …: not evaluated


# ---------------------------------------------------------------- the checker

class ExampleChecker:
    def __init__(self, model: Model, ignore_constraints=()):
        self.m = model
        self.ignore = set(ignore_constraints)
        self.ev = Evaluator(model)
        self.profiles = {p["code"]: p for p in model.profiles}

    # ---- structure helpers
    def placements(self, profile: str, seg: str) -> list[dict]:
        return [p for p in self.m.placements if p["profile"] == profile and p["segment"] == seg]

    def flavor_for(self, profile: str, segment: str) -> str | None:
        pls = self.placements(profile, hl7msg.seg_type(segment))
        if not pls:
            return None
        base = [p for p in pls if not p["slice"]]
        for sl in self.m.slicings:
            if sl["profile"] != profile or sl["segment"] != hl7msg.seg_type(segment):
                continue
            for s in sl["slices"]:
                if self.ev.run(s["assertion"], segment, 0) is True:
                    return s["flavor"]
        live = [p for p in base if not p["excluded"]] or base
        return live[0]["flavor"]

    def profile_segments(self, profile: str) -> tuple[set, set, list]:
        allowed, unsupported, required = set(), set(), []
        for p in self.m.placements:
            if p["profile"] != profile or p["slice"]:
                continue
            (unsupported if p["excluded"] else allowed).add(p["segment"])
            if p["usage"] == "R" and "." not in p["path"]:
                required.append(p["segment"])
        return allowed, unsupported - allowed, required

    # ---- element-level checks (recursive over data types)
    def check_element(self, value: str, level: int, dt_id: str, where: str, out: list):
        dt = self.m.datatypes.get(dt_id)
        if not dt:
            return
        for c in dt["constraints"]:
            if self.ev.run(c["assertion"], value, level) is False:
                desc = c["description"].replace("Element 'xxx'", where)
                out.append(("format" if c["assertion"]["op"] == "Format" else "constraint",
                            f"{where} '{value}' does not meet {dt['label']} {c['id']}: {desc}"))
        if level >= 2 or not dt["components"]:
            return
        parts = split_level(value, level)
        for i, comp in enumerate(dt["components"], 1):
            cval = parts[i - 1] if i <= len(parts) else ""
            preds = [p for p in dt["predicates"] if (p.get("target_path") or "").startswith(f"{i}[")]
            usage = comp["usage"]
            if preds:
                r = self.ev.run(preds[0]["assertion"], value, level)
                usage = preds[0]["true_usage"] if r is True else (preds[0]["false_usage"] if r is False else None)
            cwhere = f"{where}.{i}" if level == 1 else f"{where}.{i}"
            if usage == "R" and not cval.strip():
                out.append(("required", f"{cwhere} ({comp['name']}) is required but empty."))
            elif usage == "X" and cval.strip():
                out.append(("not-supported", f"{cwhere} ({comp['name']}) is not supported (X) but is valued '{cval}'."))
            if cval.strip():
                self.check_codes(cval, level + 1, comp.get("bindings", []), cwhere, comp["name"], out)
                self.check_element(cval, level + 1, comp["datatype"], cwhere, out)

    def check_codes(self, value: str, level: int, bindings: list, where: str, name: str, out: list):
        """Check a code against the value sets bound (strength R) to the element. When the element names its
        coding system (CE.3/CWE.3), only value sets of that system apply; a code from another system is not
        checked here."""
        parts = split_level(value, level) if level <= 2 else [value]
        code = parts[0].strip()
        system = parts[2].strip() if len(parts) > 2 else ""
        if not code:
            return
        sets = []
        for b in bindings:
            if b.get("strength") != "R" or b.get("path"):
                continue
            sets += [self.m.value_sets.get(v) for v in b["value_sets"]]
        sets = [v for v in sets if v and v["codes"] and not v["no_validation"]]
        if system:
            sets = [v for v in sets if any((c.get("system") or "").upper() == system.upper() for c in v["codes"][:5])]
        if not sets:
            return
        codes = {c["code"]: c for v in sets for c in v["codes"]}
        names = ", ".join(v["id"] for v in sets)
        if code not in codes:
            closed = any(v.get("extensibility") == "Closed" for v in sets)
            out.append(("code" if closed else "code-open",
                        f"{where} ({name}) code '{code}' is not in {names}" + ("" if closed else " (an open value set)") + "."))
        elif codes[code].get("usage") == "E":
            out.append(("code", f"{where} ({name}) code '{code}' is excluded (usage E) in {names}."))

    def check_segment(self, profile: str, seg: str, out: list) -> str | None:
        flavor = self.flavor_for(profile, seg)
        if not flavor:
            return None
        s = self.m.segments[flavor]
        name = s["name"]
        for f in s["fields"]:
            pos = f["position"]
            if name == "MSH" and pos in (1, 2):
                continue
            reps = [r for r in hl7msg.repetitions(seg, pos) if r.strip()] if not (name == "MSH" and pos <= 2) else []
            preds = [p for p in s["predicates"] if (p.get("target_path") or "").startswith(f"{pos}[")]
            usage = f["usage"]
            if preds:
                r = self.ev.run(preds[0]["assertion"], seg, 0)
                usage = preds[0]["true_usage"] if r is True else (preds[0]["false_usage"] if r is False else None)
            where = f"{name}-{pos}"
            if usage == "R" and not reps:
                out.append(("required", f"{where} ({f['name']}) is required in {flavor} but empty."))
            elif usage == "X" and reps:
                out.append(("not-supported", f"{where} ({f['name']}) is not supported (X) in {flavor} but is valued."))
            mx = f.get("max")
            if isinstance(mx, int) and len(reps) > mx:
                out.append(("cardinality", f"{where} ({f['name']}) has {len(reps)} repetitions; {flavor} allows {mx}."))
            for rep in reps:
                self.check_codes(rep, 1, f.get("bindings", []), where, f["name"], out)
                if f["datatype"] in self.m.datatypes:
                    self.check_element(rep, 1, f["datatype"], where, out)
        for c in s["constraints"]:
            if c["id"] in self.ignore:
                continue
            if self.ev.run(c["assertion"], seg, 0) is False:
                out.append(("constraint", f"{c['id']}: {c['description']}"))
        return flavor

    # ---- OBX co-constraints
    def order_groups(self, segs: list[str]) -> list[list[str]]:
        groups, cur = [], None
        for s in segs:
            t = hl7msg.seg_type(s)
            if t == "ORC":
                cur = [s]
                groups.append(cur)
            elif cur is not None and t in ("TQ1", "TQ2", "RXA", "RXR", "OBX", "NTE"):
                cur.append(s)
            elif t not in ("OBX", "NTE"):
                cur = None
        return groups

    def table_applies(self, table: dict, group: list[str]) -> bool | None:
        cond = table.get("condition")
        if not cond:
            return True
        # Conditions describe the group's RXA; evaluate the description's tests on that RXA.
        rxa = next((s for s in group if hl7msg.seg_type(s) == "RXA"), "")
        d = cond
        ok = True
        for field, values, neg in self._cond_tests(d):
            v = hl7msg.get(rxa, field[0], 1, field[1]) if field[1] else hl7msg.get(rxa, field[0])
            hit = v in values
            ok = ok and (not hit if neg else hit)
        return ok

    @staticmethod
    def _cond_tests(desc: str) -> list[tuple[tuple[int, int | None], set, bool]]:
        tests = []
        for m in re.finditer(r"RXA-(\d+)(?:\.(\d+))? \([^)]*\) (does not contain|contains) (?:the value |one of the values in the list: )\[?([^\]]+?)\]? \(Case", desc):
            vals = set(re.findall(r"'([^']*)'", m.group(4)))
            tests.append(((int(m.group(1)), int(m.group(2)) if m.group(2) else None), vals, m.group(3) == "does not contain"))
        return tests

    def check_cocon(self, profile: str, segs: list[str], out: list):
        tables = [tab for t in self.m.coconstraints if t["profile"] == profile for tab in t["tables"]]
        if not tables:
            return
        for gi, group in enumerate(self.order_groups(segs), 1):
            obx = [s for s in group if hl7msg.seg_type(s) == "OBX"]
            live = [t for t in tables if self.table_applies(t, group)]
            if not live:
                continue
            rows = []
            for t in live:
                rows += [(r, None) for r in t["rows"]]
                for g in t.get("groups", []):
                    rows += [(r, g) for r in g["rows"]]
            by_loinc = defaultdict(list)
            for r, g in rows:
                for w in r["when"]:
                    if w.get("code"):
                        by_loinc[w["code"]].append((r, g))
            present = {hl7msg.get(o, 3, 1, 1) for o in obx}
            for o in obx:
                loinc = hl7msg.get(o, 3, 1, 1)
                where = f"OBX-3 {loinc} (order group {gi})"
                if loinc not in by_loinc:
                    out.append(("cocon", f"{where} is not allowed by the {profile} co-constraints for this kind of Order Segment Group."))
                    continue
                types = {th.get("value") for r, _ in by_loinc[loinc] for th in r["then"] if th["field"] == "OBX-2" and th.get("value")}
                vt = hl7msg.get(o, 2)
                if types and vt not in types:
                    out.append(("cocon", f"{where}: OBX-2 is '{vt}'; the co-constraints expect {' or '.join(sorted(types))}."))
                sets = [v for r, _ in by_loinc[loinc] for th in r["then"] if th["field"] == "OBX-5" and th.get("strength") == "R"
                        for v in th.get("value_sets", [])]
                vs = [self.m.value_sets.get(v) for v in sets]
                vs = [v for v in vs if v and v["codes"] and not v["no_validation"]]
                code = hl7msg.get(o, 5, 1, 1)
                if vs and code and code not in {c["code"] for v in vs for c in v["codes"]}:
                    out.append(("cocon", f"{where}: OBX-5 code '{code}' is not in {', '.join(v['id'] for v in vs)}."))
            for t in live:
                for r in t["rows"]:
                    if r["usage"] == "R" and (r["min"] or 0) >= 1:
                        code = next((w.get("code") for w in r["when"] if w.get("code")), None)
                        if code and code not in present:
                            out.append(("cocon-missing", f"Order group {gi}: the {profile} co-constraints require an OBX with OBX-3 {code}."))
                for g in t.get("groups", []):
                    if g["usage"] == "R" and (g["min"] or 0) >= 1:
                        prim = next((r for r in g["rows"] if r.get("primary")), g["rows"][0] if g["rows"] else None)
                        code = prim and next((w.get("code") for w in prim["when"] if w.get("code")), None)
                        if code and code not in present:
                            out.append(("cocon-missing", f"Order group {gi}: the {profile} co-constraints require the group "
                                                         f"\"{g['name']}\" (OBX-3 {code})."))

    # ---- whole message
    def check_message(self, text: str) -> tuple[str | None, list[tuple[str, str]]]:
        segs = hl7msg.segments(text)
        out: list[tuple[str, str]] = []
        profile = hl7msg.profile_of(segs)
        if not segs or hl7msg.seg_type(segs[0]) != "MSH":
            return None, [("structure", "The message does not start with MSH.")]
        if not profile or profile not in self.profiles:
            return profile, [("profile", f"MSH-21 does not name a known profile (found '{hl7msg.get(segs[0], 21)}').")]
        p = self.profiles[profile]
        msh = segs[0]
        typ = (hl7msg.get(msh, 9, 1, 1), hl7msg.get(msh, 9, 1, 2), hl7msg.get(msh, 9, 1, 3))
        fixed_event = bool(re.match(r"^[A-Z]\d{2}$", p.get("event") or ""))
        if typ[0] != p["message_type"] or (fixed_event and typ[1] and typ[1] != p["event"]):
            out.append(("message-type", f"MSH-9 is {'^'.join(typ)}, but {profile} is {p['message_type']}^{p.get('event') or ''}^{p['structure']}."))
        allowed, unsupported, required = self.profile_segments(profile)
        types = [hl7msg.seg_type(s) for s in segs]
        for t in dict.fromkeys(types):
            if t in unsupported:
                out.append(("structure", f"{t} is not supported (X) in {profile}."))
            elif t not in allowed:
                out.append(("structure", f"{t} is not part of the {profile} message structure."))
        for t in dict.fromkeys(required):
            if t not in types:
                out.append(("structure", f"{profile} requires a {t} segment."))
        for s in segs:
            if hl7msg.seg_type(s) in allowed:
                self.check_segment(profile, s, out)
        self.check_cocon(profile, segs, out)
        seen, uniq = set(), []
        for k, msg in out:
            if msg not in seen:
                seen.add(msg)
                uniq.append((k, msg))
        return profile, uniq


# ---------------------------------------------------------------- entry point

def load_examples(examples_dir: Path) -> list[dict]:
    out = []
    for f in sorted(examples_dir.glob("*.yml")):
        d = read_yaml(f, None)
        if d:
            d["_file"] = f.name
            out.append(d)
    return out


def run(cards, examples_dir: Path, model_dir: Path, f, config: dict | None = None) -> dict | None:
    if not examples_dir.exists() or not Model.available(model_dir):
        return None
    examples = load_examples(examples_dir)
    if not examples:
        return None
    model = Model(model_dir)
    checker = ExampleChecker(model, (config or {}).get("example_ignore_constraints", []))
    card_ids = {c.id for c in cards}
    results = {}
    # problems that a clipped example inherits from its base are reported once, on the base example
    bases = read_yaml(examples_dir / "_meta" / "bases.yml", {}) or {}
    base_problems = {bid: {t for _, t in checker.check_message(text)[1]} for bid, text in bases.items()}
    for ex in examples:
        card = next((c for c in ex.get("cards", []) if c in card_ids), None)
        res = []
        for i, m in enumerate(ex["messages"], 1):
            profile, problems = checker.check_message(m["message"])
            inherited = base_problems.get(m.get("base"), set())
            n_inherited = sum(1 for _, t in problems if t in inherited)
            problems = [(k, t) for k, t in problems if t not in inherited]
            res.append({"profile": profile, "problems": [{"kind": k, "message": t} for k, t in problems],
                        "inherited": n_inherited, "base": m.get("base")})
            label = f" (message {i})" if len(ex["messages"]) > 1 else ""
            for kind, text in problems:
                sev = "note" if kind in ("code-open",) else "warning"
                f.add(f"example-{kind}", "examples", sev, f"Example \"{ex['title']}\"{label}: {text}",
                      card=card, location=f"ex-{ex['id']}", key=f"{i}|{text}")
        results[ex["id"]] = res
        status = (ex.get("list") or {}).get("status")
        if status in NEEDS_INPUT:
            f.add("example-needs-input", "examples", "note",
                  f"Example \"{ex['title']}\" is marked \"{status}\" in CDC's example list; it still needs an author's decision.",
                  card=card, location=f"ex-{ex['id']}")
        for sec in ex.get("unresolved_sections", []):
            f.add("example-section-unresolved", "examples", "warning",
                  f"CDC's example list places \"{ex['title']}\" in the sub-section \"{sec}\", which does not exist in the narrative. "
                  "Either the section was renamed or removed, or the list needs updating.",
                  card=card, location=f"ex-{ex['id']}", key=sec)
    meta = read_yaml(examples_dir / "_meta" / "list.yml", {}) or {}
    rows = {r["row"]: r for r in meta.get("rows", [])}
    from guidecards import norm_title
    by_title = {norm_title(c.title): c.id for c in cards}
    for n in meta.get("unmatched_rows", []):
        r = rows.get(n)
        if not r:
            continue
        card = next((by_title.get(norm_title(s.strip())) for s in r["sub_section"].split(";") if by_title.get(norm_title(s.strip()))), None)
        f.add("example-missing", "examples", "note",
              f"CDC's example list asks for \"{(r['item'] + ': ' + r['example']).strip(': ')}\" ({r['status'] or 'no status'}), "
              "but there is no drafted example for it yet.", card=card, key=f"row-{n}")
    return {"examples": examples, "results": results, "list": meta}
