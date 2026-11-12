"""Example messages on the site: on each card they illustrate, and in Appendix A (used by build_site.py).

Messages are shown whole. The segments the example is about (its clip) are highlighted, and within
them the fields that differ from the base message are marked. Hovering over a field shows its
position and name. Check results against the IGAMT profiles appear under each message.
"""

from __future__ import annotations

import html

import hl7msg
from structure_index import Model

NEEDS_INPUT = ("Question", "Need help", "Not sure what was envisioned")
SECTION_ORDER = ["VXU Message- Field Level Components", "VXU Message Scenarios", "ACK Messages Field Level Components",
                 "RSP Message Scenarios", "Z32/Z42 Field Level Components", "Multi-Message Sequences"]


def esc(text) -> str:
    return html.escape(str(text), quote=True)


class Renderer:
    def __init__(self, model: Model | None, bases: dict, results: dict, st=None):
        self.m = model
        self.bases = {k: hl7msg.segments(v) for k, v in (bases or {}).items()}
        self.results = results or {}
        self.st = st  # site_structure.Structure, for links

    def field_title(self, seg: str, pos: int) -> str:
        name = self.m.field_name(seg, pos) if self.m and seg in self.m.segment_names else None
        return f"{seg}-{pos}" + (f" {name}" if name else "")

    def segment_html(self, seg: str, clip: bool, marked: set[int], focus: set[int]) -> str:
        t = hl7msg.seg_type(seg)
        parts = seg.split("|")
        out = [f'<span class="sg">{esc(parts[0])}</span>']
        offset = 1 if t == "MSH" else 0  # MSH-1 is the separator itself
        for i, val in enumerate(parts[1:], 1):
            pos = i + offset
            cls = ["f"]
            if pos in marked:
                cls.append("chg")
            if pos in focus:
                cls.append("focus")
            title = self.field_title(t, pos)
            out.append('<span class="bar">|</span>' + (f'<span class="{" ".join(cls)}" title="{esc(title)}">{esc(val)}</span>' if val else ""))
        return f'<span class="seg{" clip" if clip else ""}">{"".join(out)}</span>'

    def message_html(self, ex: dict, k: int, m: dict) -> str:
        segs = hl7msg.segments(m["message"])
        base = self.bases.get(m.get("base")) or []
        from_clip = set(m.get("from_clip") or [])
        focus_fields = {}
        for ref in ex.get("focus", []):
            seg, _, rest = ref.partition("-")
            focus_fields.setdefault(seg, set()).add(int(rest.split(".")[0]))
        lines = []
        for i, s in enumerate(segs):
            clip = i in from_clip and bool(base)
            marked = set(hl7msg.changed_fields(s, base)) if clip else set()
            lines.append(self.segment_html(s, clip, marked, focus_fields.get(hl7msg.seg_type(s), set())))
        res = (self.results.get(ex["id"]) or [{}] * len(ex["messages"]))[k] if self.results.get(ex["id"]) else {}
        problems = res.get("problems", [])
        profile = res.get("profile")
        check = ""
        if profile:
            plink = (f'<a href="{self.st.profile_href(profile, self.root)}">{esc(profile)}</a>' if self.st else esc(profile))
            if problems:
                lis = "".join(f"<li>{esc(p['message'])}</li>" for p in problems)
                check = (f'<details class="ex-check bad"><summary>⚠ {len(problems)} problem{"s" if len(problems) != 1 else ""} '
                         f'against the {plink} profile</summary><ul>{lis}</ul></details>')
            else:
                check = f'<p class="ex-check ok">✓ No problems found against the {plink} profile' + \
                        (" (beyond those in the base message)" if res.get("inherited") else "") + ".</p>"
        label = f'<p class="ex-label">{esc(m["label"])}</p>' if m.get("label") and m["label"] not in ex["title"] else ""
        legend = ' <span class="mini">Highlighted: what this example shows; marked fields differ from the base message.</span>' if base else ""
        text = esc(m["message"])
        return (f'{label}<div class="hl7-wrap"><button type="button" class="hl7-copy" data-text="{text}">Copy</button>'
                f'<pre class="hl7" tabindex="0">{"".join(lines)}</pre></div>{legend}{check}')

    def example_html(self, ex: dict, root: str, by_id: dict, current_card: str | None = None) -> str:
        self.root = root
        status = (ex.get("list") or {}).get("status", "")
        chips = []
        if ex.get("profile"):
            chips.append(f'<span class="chip">{esc(ex["profile"])}</span>')
        if ex.get("kind") == "sequence":
            chips.append(f'<span class="chip">{len(ex["messages"])} messages</span>')
        if ex.get("kind") == "base":
            chips.append('<span class="chip">base message</span>')
        if status in NEEDS_INPUT:
            chips.append(f'<span class="chip warn" title="Status in CDC\'s example list">{esc(status)}</span>')
        notes = "".join(f"<p>{esc(n)}</p>" for n in ex.get("notes", []))
        msgs = "".join(self.message_html(ex, k, m) for k, m in enumerate(ex["messages"]))
        others = [by_id[c] for c in ex.get("cards", []) if c in by_id and c != current_card]
        also = ("<p class='mini'>Also on: " + ", ".join(f'<a href="{root}{c.id}/index.html">{esc(c.number)} {esc(c.title)}</a>' for c in others)
                + "</p>") if others else ""
        return (f'<article class="example" id="ex-{esc(ex["id"])}"><header><h3>{esc(ex["title"])}</h3>{"".join(chips)}'
                f'<a class="s-id" href="#ex-{esc(ex["id"])}" title="Link to this example">#</a></header>{notes}{msgs}{also}</article>')

    def card_section(self, examples: list[dict], root: str, by_id: dict, card_id: str) -> str:
        if not examples:
            return ""
        body = "".join(self.example_html(ex, root, by_id, card_id) for ex in examples)
        return (f'<section class="examples" aria-labelledby="ex-h"><h2 id="ex-h">Example{"s" if len(examples) > 1 else ""}</h2>'
                f'<p class="mini">Draft examples, checked against the IGAMT profiles on every build. '
                f'<a href="{root}examples/index.html">All examples</a>.</p>{body}</section>')

    def index_page(self, examples: list[dict], list_meta: dict, by_id: dict, root: str) -> str:
        self.root = root
        groups: dict[str, list] = {}
        for ex in examples:
            sec = (ex.get("list") or {}).get("section") or ("Base messages" if ex.get("kind") == "base" else "Other examples")
            groups.setdefault(sec, []).append(ex)
        order = ["Base messages"] + SECTION_ORDER + [g for g in groups if g not in SECTION_ORDER and g != "Base messages"]
        total = sum(1 for _ in examples)
        clean = sum(1 for ex in examples if all(not r.get("problems") for r in self.results.get(ex["id"], [])))
        needs = sum(1 for ex in examples if (ex.get("list") or {}).get("status") in NEEDS_INPUT)
        rows_by = {r["row"]: r for r in list_meta.get("rows", [])}
        missing = [rows_by[n] for n in list_meta.get("unmatched_rows", []) if n in rows_by]
        parts = []
        for g in order:
            if g not in groups:
                continue
            lis = []
            for ex in groups[g]:
                res = self.results.get(ex["id"], [])
                n = sum(len(r.get("problems", [])) for r in res)
                status = (ex.get("list") or {}).get("status", "")
                cards = ", ".join(f'<a href="{root}{c}/index.html#ex-{esc(ex["id"])}">{esc(by_id[c].number)} {esc(by_id[c].title)}</a>'
                                  for c in ex.get("cards", []) if c in by_id)
                lis.append(f'<tr id="ex-{esc(ex["id"])}"><td><a href="{root}{ex["cards"][0]}/index.html#ex-{esc(ex["id"])}">{esc(ex["title"])}</a>'
                           if ex.get("cards") and ex["cards"][0] in by_id else f'<tr><td>{esc(ex["title"])}')
                lis[-1] += (f'</td><td>{esc(ex.get("profile") or "")}</td><td>{cards}</td>'
                            f'<td>{"<span class=chip>" + str(len(ex["messages"])) + " msgs</span>" if ex.get("kind") == "sequence" else ""}'
                            f'{"<span class=\'chip warn\'>" + esc(status) + "</span>" if status in NEEDS_INPUT else ""}</td>'
                            f'<td class="n">{"✓" if not n else "⚠ " + str(n)}</td></tr>')
            parts.append(f'<section><h2>{esc(g)}</h2><div class="table-wrap"><table class="model"><thead><tr><th>Example</th><th>Profile</th>'
                         f'<th>Shown on</th><th>Status</th><th>Checks</th></tr></thead><tbody>{"".join(lis)}</tbody></table></div></section>')
        miss = "".join(f"<li><strong>{esc(r['item'])}</strong>: {esc(r['example'])} <span class='mini'>({esc(r['sub_section'])}; {esc(r['status'])})</span></li>"
                       for r in missing)
        return f"""<article class="page model-page">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}index.html">Home</a></nav>
<h1><span class="num">A</span> Example Messages</h1>
<p>Draft example messages from CDC's example list and the drafted samples. Each example appears on the sections it illustrates.
Examples drafted as clips (only the segments that matter) are completed from a base message, so that every example is a whole
message. Each one is checked against the IGAMT profiles on every build: segments, required and unsupported fields, codes,
date and time formats, conformance statements, and OBX co-constraints.</p>
<p class="stats">{total} examples · {clean} with no problems of their own · {needs} still marked as needing input in CDC's list ·
{len(missing)} requested in the list but not drafted yet.</p>
{''.join(parts)}
{f'<section><h2>Requested but not drafted yet</h2><ul>{miss}</ul></section>' if miss else ''}
</article>"""
