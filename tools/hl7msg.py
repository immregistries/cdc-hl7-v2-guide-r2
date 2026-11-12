"""Small HL7 v2 (ER7) helpers for example messages: parse, address fields, assemble from a base.

Assembly turns an authored *clip* (only the segments an example is about) into a complete message:

- A clip that starts with MSH is already a complete message and is used as written.
- Header segments in the clip (MSH, PID, PD1, NK1, MSA, QAK, QPD, ERR, RCP) replace the base's
  segments of the same type.
- If the clip has an ORC, its order segments (ORC, RXA, RXR, OBX) replace the base's whole order part.
- If the clip has RXA but no ORC, the base ORC is kept and the RXA is replaced. RXR and OBX come from
  the clip; the base's RXR and OBX are kept only for an administered dose (RXA-9.1 '00'). For a
  refused or not-administered dose (RXA-20 'RE' or 'NA'), the kept ORC gets ORC-3 '9999' as the guide
  requires.
- If the clip has only OBX segments, they replace the base's OBX segments.
"""

from __future__ import annotations

import re

SEG_RE = re.compile(r"^[A-Z][A-Z0-9]{2}\|")
HEADER = {"MSH", "SFT", "PID", "PD1", "NK1", "PV1", "PV2", "GT1", "IN1", "IN2", "IN3", "MSA", "ERR", "QAK", "QPD", "RCP"}
ORDER = {"ORC", "TQ1", "TQ2", "RXA", "RXR", "OBX", "NTE"}


def segments(text: str) -> list[str]:
    """Segment lines. Segments run together on one line (separated by spaces) are split apart."""
    out = []
    for line in re.split(r"\r\n|\r|\n", text or ""):
        line = line.strip()
        if SEG_RE.match(line):
            out.extend(p.strip() for p in re.split(r"\s+(?=(?:MSH|PID|PD1|NK1|ORC|RXA|RXR|OBX|NTE|MSA|ERR|QAK|QPD|RCP|TQ1|PV1|IN1)\|)", line) if p.strip())
    return out


def complete(clip: list[str]) -> bool:
    """A clip is a complete message when it has MSH and a segment that only whole messages have."""
    types = {seg_type(s) for s in clip}
    return bool(clip) and seg_type(clip[0]) == "MSH" and bool(types & {"PID", "MSA", "QPD", "QAK", "ORC"})


def seg_type(seg: str) -> str:
    return seg[:3]


def fields(seg: str) -> list[str]:
    """Field list where index n is SEG-n (index 0 is the segment name). MSH-1 is the field separator."""
    parts = seg.split("|")
    if parts[0] == "MSH":
        return ["MSH", "|"] + parts[1:]
    return parts


def get(seg: str, field: int, rep: int = 1, comp: int | None = None, sub: int | None = None) -> str:
    f = fields(seg)
    if field >= len(f):
        return ""
    value = f[field]
    if not (seg_type(seg) == "MSH" and field in (1, 2)):
        reps = value.split("~")
        value = reps[rep - 1] if rep <= len(reps) else ""
        if comp is not None:
            comps = value.split("^")
            value = comps[comp - 1] if comp <= len(comps) else ""
            if sub is not None:
                subs = value.split("&")
                value = subs[sub - 1] if sub <= len(subs) else ""
    return value.strip()


def repetitions(seg: str, field: int) -> list[str]:
    f = fields(seg)
    if field >= len(f) or not f[field]:
        return []
    if seg_type(seg) == "MSH" and field in (1, 2):
        return [f[field]]
    return f[field].split("~")


def set_field(seg: str, field: int, value: str) -> str:
    parts = seg.split("|")
    idx = field - 1 if parts[0] == "MSH" else field
    while len(parts) <= idx:
        parts.append("")
    parts[idx] = value
    return "|".join(parts)


def profile_of(segs: list[str]) -> str | None:
    msh = next((s for s in segs if seg_type(s) == "MSH"), None)
    if not msh:
        return None
    for rep in repetitions(msh, 21):
        code = rep.split("^")[0].strip()
        if re.match(r"^Z\d{2}$", code):
            return code
    return None


def assemble(base: list[str], clip: list[str]) -> tuple[list[str], list[int]]:
    """Return (message segments, indexes of segments that came from the clip)."""
    if complete(clip):
        return list(clip), list(range(len(clip)))
    out: list[tuple[str, bool]] = [(s, False) for s in base]
    clip_types = {seg_type(s) for s in clip}

    # header segments: replace by type, keeping the base position
    for t in [t for t in dict.fromkeys(seg_type(s) for s in clip) if t in HEADER]:
        new = [(s, True) for s in clip if seg_type(s) == t]
        idx = [i for i, (s, _) in enumerate(out) if seg_type(s) == t]
        if idx:
            out = out[:idx[0]] + new + [x for i, x in enumerate(out) if i > idx[0] and i not in idx]
        else:  # insert before the order part (or at the end)
            first_order = next((i for i, (s, _) in enumerate(out) if seg_type(s) in ORDER), len(out))
            out = out[:first_order] + new + out[first_order:]

    order_clip = [s for s in clip if seg_type(s) in ORDER]
    if order_clip:
        first_order = next((i for i, (s, _) in enumerate(out) if seg_type(s) in ORDER), len(out))
        head, base_order = out[:first_order], out[first_order:]
        if "ORC" in clip_types:
            order = [(s, True) for s in order_clip]
        elif "RXA" in clip_types:
            rxa = next(s for s in order_clip if seg_type(s) == "RXA")
            administered = get(rxa, 9, 1, 1) == "00"
            not_given = get(rxa, 20) in ("RE", "NA")
            orc = next((s for s, _ in base_order if seg_type(s) == "ORC"), None)
            order = []
            if orc:
                if not_given:
                    orc = set_field(orc, 3, "9999^CDC-AIRA")
                order.append((orc, False))
            order += [(s, True) for s in order_clip if seg_type(s) in ("RXA",)]
            rxr = [s for s in order_clip if seg_type(s) == "RXR"]
            obx = [s for s in order_clip if seg_type(s) in ("OBX", "NTE")]
            if rxr:
                order += [(s, True) for s in rxr]
            elif administered:
                order += [(s, False) for s, _ in base_order if seg_type(s) == "RXR"]
            if obx:
                order += [(s, True) for s in obx]
            elif administered:
                order += [(s, False) for s, _ in base_order if seg_type(s) == "OBX"]
        else:  # OBX only
            order = [(s, False) for s, _ in base_order if seg_type(s) not in ("OBX", "NTE")] + [(s, True) for s in order_clip]
        out = head + order
    return [s for s, _ in out], [i for i, (_, c) in enumerate(out) if c]


def changed_fields(seg: str, base_segs: list[str]) -> list[int]:
    """Field numbers that differ from the first base segment of the same type (all, if none)."""
    t = seg_type(seg)
    other = next((s for s in base_segs if seg_type(s) == t), None)
    f = fields(seg)
    if other is None:
        return [i for i in range(1, len(f)) if f[i]]
    g = fields(other)
    n = max(len(f), len(g))
    return [i for i in range(1, n) if (f[i] if i < len(f) else "").strip() != (g[i] if i < len(g) else "").strip()]
