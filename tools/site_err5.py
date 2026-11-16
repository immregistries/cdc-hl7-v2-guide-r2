"""Appendix D: the National Set of ERR-5 Application Error Codes (data/err5-codes.yml), compared with HL70533_IZ01."""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from guidecards import read_yaml

VALUE_SET = "HL70533_IZ01"
ERR5_CARD = "err-5-application-error-code"
PRIORITY_VERB = {"High": ("SHALL", "shall"), "Medium": ("SHOULD", "should"), "Low": ("MAY", "may")}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def load(repo: Path) -> dict | None:
    data = read_yaml(repo / "data" / "err5-codes.yml", None)
    if not data:
        return None
    igamt = set()
    vs_path = repo / "model" / "value-sets.json"
    if vs_path.exists():
        for vs in json.loads(vs_path.read_text(encoding="utf-8")):
            if isinstance(vs, dict) and vs.get("id") == VALUE_SET:
                igamt = {c["code"] for c in vs.get("codes", [])}
    data["igamt"] = igamt
    return data


def _range_of(code: str, ranges: list[dict]) -> str:
    n = int(code)
    for r in ranges:
        lo, hi = (int(x) for x in r["range"].split("–"))
        if lo <= n <= hi:
            return r["range"]
    return ""


def _see(ref: str) -> str:
    """A "See also" entry: one code, or a range such as 3039-3041 (linked to its first code)."""
    first = ref.split("-")[0].strip()
    label = ref.replace("-", "–")
    return f'<a href="#err5-{esc(first)}">{esc(label)}</a>' if first.isdigit() else esc(ref)


def _priority(p: str) -> str:
    if p in PRIORITY_VERB:
        word, cls = PRIORITY_VERB[p]
        return f'<span class="err5-prio p-{cls}">{esc(p)}</span><span class="mini"> {word}</span>'
    return f'<span class="mini">{esc(p)}</span>'


def page(data: dict, root: str, by_id: dict) -> str:
    codes, ranges, igamt = data["codes"], data["ranges"], data["igamt"]
    national = {c["code"] for c in codes}
    prio = Counter(c["priority"] for c in codes)
    in_both = national & igamt
    only_igamt = sorted(igamt - national, key=int)
    card = by_id.get(ERR5_CARD)
    card_link = (f'<a href="{root}{card.id}/index.html">{esc(card.number)} {esc(card.title)}</a>' if card else "ERR-5: Application Error Code")

    groups = []
    for r in ranges:
        rows = []
        for c in codes:
            if _range_of(c["code"], ranges) != r["range"]:
                continue
            notes = []
            if c.get("notes"):
                notes.append(esc(c["notes"]))
            if c.get("see_also"):
                notes.append("See also " + ", ".join(_see(s) for s in c["see_also"]))
            status = c.get("status", "")
            status_html = "" if status == "Active" else f'<span class="err5-status s-{esc(status.lower().replace(" ", "-"))}">{esc(status)}</span>'
            ig = '<span class="err5-ig yes" title="In the IGAMT value set">✓</span>' if c["code"] in igamt else \
                 '<span class="err5-ig no" title="Not in the IGAMT value set">—</span>'
            rows.append(
                f'<tr id="err5-{esc(c["code"])}"><td class="code"><code>{esc(c["code"])}</code></td>'
                f'<td><strong>{esc(c["concept"])}</strong> {status_html}'
                + (f'<p>{esc(c["description"])}</p>' if c.get("description") and c["description"] != c["concept"] else "")
                + (f'<p class="mini">{" · ".join(notes)}</p>' if notes else "")
                + f'</td><td>{_priority(c["priority"])}</td><td class="ig">{ig}</td></tr>')
        n_ig = sum(1 for c in codes if _range_of(c["code"], ranges) == r["range"] and c["code"] in igamt)
        n = len(rows)
        groups.append(
            f'<section class="err5-range" id="range-{esc(r["range"].split("–")[0])}"><h2><span class="num">{esc(r["range"])}</span> {esc(r["description"])}</h2>'
            f'<p class="mini">{n} code{"s" if n != 1 else ""} · {n_ig} in {VALUE_SET}</p>'
            f'<table class="err5"><thead><tr><th>Code</th><th>Concept</th><th>Priority</th><th>IGAMT</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></section>')

    range_rows = "".join(
        f'<tr><td class="nowrap"><a href="#range-{esc(r["range"].split("–")[0])}">{esc(r["range"])}</a></td><td>{esc(r["description"])}</td>'
        f'<td class="mini">{esc(r.get("example", ""))}</td></tr>' for r in ranges)
    extra_ig = (f' {VALUE_SET} also has {len(only_igamt)} code{"s" if len(only_igamt) != 1 else ""} not in the national set: '
                + ", ".join(only_igamt) + "." if only_igamt else "")
    return f"""<article class="page err5-page">
<p class="eyebrow">Appendix D</p>
<h1>National ERR-5 Application Error Codes</h1>
<p class="callout"><strong>Pending publication.</strong> These codes are from version {esc(data.get('version', ''))} of AIRA's
<em>{esc(data['title'])}</em>, which is being prepared for posting on the AIRA repository. The published set is
authoritative; this page will be updated from it.</p>
<p class="lede">ERR-5 identifies what the problem was, using a code from this national set ({card_link}). Each code has an
implementation priority: IIS SHALL implement High priority codes, SHOULD implement Medium priority codes, and MAY implement
Low priority codes. Implementing a code means returning it when the condition is detected; the ERR-4 severity, and whether
the data is accepted, remain local decisions.</p>
<p>If a concept is not in the set, ask {esc(data.get('maintainer', 'AIRA'))} to add a code (<a href="mailto:{esc(data.get('contact', ''))}">{esc(data.get('contact', ''))}</a>)
rather than defining a local one. Codes with status <em>Not Specific</em> are general and should be used only when no more
specific code applies; <em>Deprecated</em> and <em>Do Not Use</em> codes should not be used.</p>
<p class="stats">{len(codes)} codes: {prio['High']} High, {prio['Medium']} Medium, {prio['Low']} Low, {prio['N/A']} not applicable
(deprecated or do not use).</p>
<h2>Compared with the IGAMT value set</h2>
<p>The value set bound to ERR-5 in the profiles, <a href="{root}structure/value-sets/hl70533-iz01/index.html"><code>{VALUE_SET}</code></a>,
has {len(igamt)} codes, {len(in_both)} of them in the national set. {len(national - igamt)} national codes, including
{sum(1 for c in codes if c['priority'] == 'High' and c['code'] not in igamt)} of the {prio['High']} High priority codes, are not in
it.{extra_ig} The IGAMT column below marks the codes the value set has.</p>
<h2>Code ranges</h2>
<table class="err5 ranges"><thead><tr><th>Range</th><th>Type of issue</th><th>Example</th></tr></thead><tbody>{range_rows}</tbody></table>
{''.join(groups)}
</article>"""


def card_panel(card_id: str, data: dict | None, root: str) -> str:
    if not data or card_id != ERR5_CARD:
        return ""
    high = sum(1 for c in data["codes"] if c["priority"] == "High")
    return (f'<section class="related"><h2>National ERR-5 code set</h2><p><a href="{root}err5-codes/index.html">Appendix D, '
            f'National ERR-5 Application Error Codes</a>: all {len(data["codes"])} codes with their implementation priorities '
            f'({high} High). Pending publication by AIRA.</p></section>')
