"""The "Changes from Release 1.5" page: this guide compared with the Release 1.5 baseline (tools/diff_r15.py).

Release 1.5 is represented as NIST's conformance profiles (the source of truth for format and validation, what
systems were tested against) plus the guidance in the 2018 narrative. This page shows the structural comparison
(tools/diff_r15.py) and the reviewed narrative crosswalk (quality/r15/narrative/, read by tools/r15_narrative.py).
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import diff_r15
import r15_narrative
from guidecards import write_text

NIST_TOOL = "https://tools.valitheus.com/immunization-edition2/#/doc"
CDC_PAGE = "https://www.cdc.gov/iis/technical-guidance/hl7.html"
STATUS_LABEL = {"changed": "Changed", "removed": "Removed", "added": "Added", "reworded": "Reworded",
                "renumbered": "Renumbered", "split": "Split", "same": "Same"}
STATUS_HELP = {
    "changed": "Same ID, different test",
    "removed": "In Release 1.5, not in this guide",
    "added": "New in this guide",
    "reworded": "Same test, different wording",
    "renumbered": "Same test, different ID",
    "split": "Divided into several statements (IZ-17a, IZ-17b, ...)",
    "same": "Unchanged",
}
KIND_LABEL = {"tightened": "Tightened", "loosened": "Loosened", "added": "Added", "removed": "Removed", "changed": "Changed"}
LONG = 12  # code lists longer than this are folded


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def load(repo: Path, by_id: dict) -> dict | None:
    if not (repo / "prior" / "release-1.5" / "model" / "profiles.json").exists() or not (repo / "model" / "profiles.json").exists():
        return None
    data = diff_r15.compute(repo)
    data["narrative"] = r15_narrative.load(repo, by_id)
    data["by_id"] = by_id
    return data


def _el_link(label: str, root: str) -> str:
    m = re.match(r"^([A-Z0-9]{3})-(\d+)", label)
    if not m:
        return f"<code>{esc(label)}</code>"
    return f'<a href="{root}structure/segments/{slug(m.group(1))}/index.html#f{m.group(2)}"><code>{esc(label)}</code></a>'


def _profiles(ps: list[str]) -> str:
    if len(ps) == len(diff_r15.PROFILE_ORDER):
        return '<span class="mini">all</span>'
    return f'<span class="mini">{esc(" ".join(ps))}</span>'


def _codes(codes: list[str]) -> str:
    if not codes:
        return "—"
    text = ", ".join(codes)
    if len(codes) <= LONG:
        return esc(text)
    return f'<details><summary>{len(codes)} codes</summary><p class="mini">{esc(text)}</p></details>'


def _value(v) -> str:
    v = str(v)
    return "—" if v in ("-", "") else esc(v)


def page(data: dict, root: str) -> str:
    rows = data["rows"]
    seg_rows = [r for r in rows if r["aspect"] == "segment"]
    field_rows = [r for r in rows if r["aspect"] != "segment"]
    kinds = {k: sum(1 for r in field_rows if r["kind"] == k and r["aspect"] == "usage") for k in ("tightened", "loosened")}
    counts = data["counts"]

    # message structure
    seg_html = "".join(
        f'<tr><td><code>{esc(r["element"])}</code>{" <span class=mini>group</span>" if r["name"] == "group" else ""}</td>'
        f'<td>{_value(r["old"])}</td><td>{_value(r["new"])}</td><td>{_profiles(r["profiles"])}</td></tr>' for r in seg_rows)

    # fields and components, by segment
    by_seg: dict[str, list] = {}
    for r in field_rows:
        by_seg.setdefault(r["element"][:3], []).append(r)
    seg_sections = []
    for seg in sorted(by_seg):
        trs = []
        for r in by_seg[seg]:
            kind = r["kind"] if r["aspect"] in ("usage", "element") else ""
            trs.append(
                f'<tr class="k-{esc(r["kind"])}"><td class="nowrap">{_el_link(r["element"], root)}</td><td>{esc(r["name"])}</td>'
                f'<td>{esc(diff_r15.ASPECT_LABEL[r["aspect"]])}'
                + (f' <span class="r15-kind k-{esc(kind)}">{esc(KIND_LABEL[kind])}</span>' if kind in ("tightened", "loosened") else "")
                + f'</td><td>{_value(r["old"])}</td><td>{_value(r["new"])}</td><td>{_profiles(r["profiles"])}</td></tr>')
        seg_sections.append(
            f'<section id="seg-{esc(slug(seg))}"><h3>{esc(seg)}</h3>'
            f'<table class="r15"><thead><tr><th>Element</th><th>Name</th><th>What changed</th><th>Release 1.5</th>'
            f'<th>This guide</th><th>Profiles</th></tr></thead><tbody>{"".join(trs)}</tbody></table></section>')
    seg_index = " · ".join(f'<a href="#seg-{esc(slug(s))}">{esc(s)}</a>' for s in sorted(by_seg))

    # codes
    code_html = "".join(
        f'<tr><td><code>{esc(c["value_set"])}</code></td><td>{_codes(c["added"])}</td><td>{_codes(c["removed"])}</td>'
        f'<td>{", ".join(_el_link(el, root) for el, _ in c["elements"])}</td></tr>' for c in data["code_changes"])

    # conformance statements
    st = data["statements"]
    st_counts = {k: sum(1 for x in st if x["status"] == k) for k in STATUS_LABEL}
    st_html = "".join(
        f'<tr id="st-{esc(x["id"])}" class="s-{esc(x["status"])}"><td class="sid"><code>{esc(x["id"])}</code>'
        + (f'<br><span class="mini">now</span> <code>{esc(x["new_id"])}</code>' if x["new_id"] not in ("", x["id"]) else "")
        + '</td>'
        f'<td><span class="r15-status s-{esc(x["status"])}">{esc(STATUS_LABEL[x["status"]])}</span></td>'
        f'<td>{esc(x["old"]) or "—"}</td><td>{esc(x["new"]).replace(chr(10), "<br>") or "—"}</td>'
        f'<td class="mini">{esc(", ".join(x["contexts"]))}</td></tr>'
        for x in st if x["status"] != "same")
    same = ", ".join(f"<code>{esc(x['id'])}</code>" for x in st if x["status"] == "same")

    # lengths
    dropped = data["length_dropped"]
    len_list = ", ".join(f"<code>{esc(el)}</code>" for el, _, _ in dropped)

    return f"""<article class="page r15-page">
<p class="eyebrow">Review</p>
<h1>Changes from Release 1.5</h1>
<p class="lede">How this guide differs from the <em>HL7 Version 2.5.1 Implementation Guide for Immunization Messaging,
Release 1.5, 2018 Update</em>.</p>
<h2>What Release 1.5 means here</h2>
<p>For <strong>format and validation</strong> (message structure, usage, cardinality, data types, lengths, value sets, and
conformance statements), Release 1.5 is the set of conformance profiles NIST built from the 2018 Update for its
<a href="{NIST_TOOL}" rel="noopener" target="_blank">Immunization Test Suite</a>. NIST studied the guide closely to build
them, and they are what immunization systems were tested and certified against, so they are the baseline. Where the
tables in the 2018 document differ from NIST's reading, NIST's profiles are used and the difference is not reported.</p>
<p>For <strong>everything else</strong>, the guidance in the narrative, Release 1.5 is the
<a href="{CDC_PAGE}" rel="noopener" target="_blank">2018 Update document</a> published by CDC.</p>
<p>Codes in externally maintained code systems ({esc(", ".join(data["external"]))}) change all the time and are not compared;
only a change in which of them a field uses is shown.</p>
<p><a class="button" href="changes.csv" download>Download all changes (CSV)</a></p>

<h2>Summary</h2>
<ul class="r15-summary">
<li>{counts.get("segment", 0)} changes to message structure (segments and groups)</li>
<li>Conformance statements: {st_counts["changed"]} changed, {st_counts["removed"]} removed, {st_counts["added"]} added,
{st_counts["reworded"]} reworded, {st_counts["renumbered"]} renumbered, {st_counts["split"]} split into parts, {st_counts["same"]} unchanged</li>
<li>{counts.get("usage", 0)} usage changes: {kinds["tightened"]} tightened, {kinds["loosened"]} loosened, the rest changed in other ways</li>
<li>{counts.get("condition", 0)} changed conditions (predicates) for conditional (C) elements</li>
<li>{counts.get("cardinality", 0)} cardinality changes and {counts.get("datatype", 0)} data type changes</li>
<li>{counts.get("binding", 0)} changes to the value sets fields use, and {len(data["code_changes"])} changes to the codes in them</li>
<li>{counts.get("length", 0)} changed lengths; {len(dropped)} elements no longer state a length</li>
{_narrative_bullet(data.get("narrative") or [])}
</ul>
<p class="mini">Fields and components are compared where either guide constrains them (usage other than O or X);
components are compared two levels deep. A change that is the same in several profiles is shown once.</p>

<h2 id="structure">Message structure</h2>
<table class="r15"><thead><tr><th>Segment or group</th><th>Release 1.5</th><th>This guide</th><th>Profiles</th></tr></thead>
<tbody>{seg_html}</tbody></table>

<h2 id="fields">Fields and components</h2>
<p class="mini">By segment: {seg_index}</p>
{"".join(seg_sections)}

<h2 id="statements">Conformance statements</h2>
<p>Matched by ID (the IZ numbers carry over) and compared by the test each one makes, not its wording.
{"; ".join(f"{esc(STATUS_LABEL[k])}: {esc(STATUS_HELP[k].lower())}" for k in ("changed", "reworded", "renumbered", "split"))}.
A split statement should be checked to see that its parts together test the same thing.</p>
<table class="r15"><thead><tr><th>ID</th><th>Status</th><th>Release 1.5</th><th>This guide</th><th>Where</th></tr></thead>
<tbody>{st_html}</tbody></table>
<details><summary>Unchanged ({st_counts["same"]})</summary><p class="mini">{same}</p></details>

<h2 id="codes">Codes in value sets</h2>
<p>Codes allowed in Release 1.5 and not in this guide (removed), and the reverse (added), for the fields that use each
value set.</p>
<table class="r15"><thead><tr><th>Value set</th><th>Added</th><th>Removed</th><th>Fields</th></tr></thead>
<tbody>{code_html}</tbody></table>

<h2 id="lengths">Lengths</h2>
<p>Release 1.5 states a length for {len(dropped)} elements that this guide does not. Elements whose stated length changed are
listed with the fields above.</p>
<details><summary>Elements that no longer state a length</summary><p class="mini">{len_list}</p></details>

{narrative_section(data.get("narrative") or [], data.get("by_id") or {}, root)}
</article>"""


# ---------------------------------------------------------------- narrative crosswalk

def _narrative_bullet(parts: list[dict]) -> str:
    if not parts:
        return ""
    c = r15_narrative.counts(parts)
    return (f'<li>Narrative guidance (<a href="#narrative">below</a>): {c.get("changed", 0)} changed, {c.get("dropped", 0)} not '
            f'carried forward, {c.get("partial", 0)} partly carried forward, {c.get("expanded", 0)} expanded, '
            f'{c.get("same", 0)} the same</li>')


def _guide_link(ref: str, by_id: dict, root: str) -> str:
    card = by_id[r15_narrative._ref_card(ref)]
    if "--s" in ref:
        return f'<a href="{root}{card.id}/index.html#{esc(ref)}">{esc(card.number)} s{esc(ref.rsplit("--s", 1)[1])}</a>'
    return f'<a href="{root}{card.id}/index.html">{esc(card.number)} {esc(card.title)}</a>'


def _result(result: str) -> str:
    label, help_text = r15_narrative.RESULTS[result]
    return f'<span class="r15-result r-{esc(result)}" title="{esc(help_text)}">{esc(label)}</span>'


def _flat(text) -> str:
    return " ".join(str(text or "").split())


def _first_sentence(text) -> str:
    text = _flat(text)
    m = re.match(r"(.+?[a-z0-9)\"]\.)(\s|$)", text)  # a full stop after a word, not "e.g." or "4.5.2"
    return m.group(1) if m else text


def narrative_section(parts: list[dict], by_id: dict, root: str) -> str:
    if not parts:
        return '<h2 id="narrative">Guidance in the narrative</h2>\n<p class="empty">The narrative comparison is not available.</p>'
    counts = r15_narrative.counts(parts)
    total = sum(counts.values())
    count_html = " · ".join(f'{_result(k)} {counts[k]}' for k in r15_narrative.RESULTS if counts.get(k))

    key = [f'<li>{_result(it["result"])} <a href="#{esc(it["id"])}">{esc(it["section"])}</a>: '
           f'{esc(_first_sentence(it.get("note") or it["r15"]))}</li>'
           for _, it in r15_narrative.items(parts) if it["result"] in r15_narrative.ATTENTION]

    chapters = []
    for p in parts:
        rows = []
        for it in p.get("items", []):
            links = ", ".join(_guide_link(r, by_id, root) for r in it.get("guide") or []) or "—"
            rec = (f'<p class="r15-rec"><strong>Suggested:</strong> {esc(_flat(it["recommendation"]))}</p>'
                   if it.get("recommendation") else "")
            note = f'<p>{esc(_flat(it["note"]))}</p>' if it.get("note") else ""
            rows.append(
                f'<tr id="{esc(it["id"])}" class="r-{esc(it["result"])}"><td class="sid"><code>{esc(it["id"])}</code></td>'
                f'<td>{esc(it["section"])}<br><span class="mini">p. {esc(it.get("page", ""))}</span></td>'
                f'<td>{_result(it["result"])}</td><td>{esc(_flat(it["r15"]))}</td>'
                f'<td>{note}{rec}<p class="mini">{links}</p></td></tr>')
        cid = f'narr-{slug(str(p.get("chapter", p["file"])))}'
        summary = f'<p>{esc(_flat(p["summary"]))}</p>' if p.get("summary") else ""
        chapters.append(
            f'<section id="{esc(cid)}"><h3>{esc(p.get("title", ""))} <span class="mini">(2018 pages {esc(p.get("pages", ""))})</span></h3>'
            f'{summary}<table class="r15 r15-narr"><thead><tr><th>ID</th><th>Release 1.5 section</th><th>Result</th>'
            f'<th>What Release 1.5 says</th><th>This guide</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>')
    chapter_index = " · ".join(
        f'<a href="#narr-{esc(slug(str(p.get("chapter", p["file"]))))}">{esc(p.get("title", ""))}</a>' for p in parts)

    return f"""<h2 id="narrative">Guidance in the narrative</h2>
<p>The 2018 narrative was read section by section, and each piece of guidance was looked for in this guide. The parts
read were chapters 1 to 3; the introduction, interaction, and dynamic definition of each profile (chapters 5 to 12);
the batch chapter; the guidance around the example messages in Appendix B; and the addendum material in Appendix C.
Data types, segment and code tables, and the example messages themselves are format, governed by the profiles above.
Guidance that the profiles now carry is marked {_result("format")} and not compared further.</p>
<p>Not yet compared: the field notes and comments in the 2018 segment and data type tables. A second pass will check
them against this guide and record only what they add or where they conflict.</p>
<p>{total} items: {count_html}. <a href="narrative.csv" download>Download the narrative comparison (CSV)</a></p>
<h3 id="narrative-key">Changed or not carried forward</h3>
<ul class="r15-key">{"".join(key)}</ul>
<p class="mini">By part: {chapter_index}</p>
{"".join(chapters)}"""


def build_page(out: Path, data: dict, write) -> None:
    """Writes r15/index.html (through write(path, body)), r15/changes.csv, and r15/narrative.csv."""
    write(out / "r15" / "index.html", page(data, "../"))
    write_text(out / "r15" / "changes.csv", diff_r15.to_csv(data))
    if data.get("narrative"):
        write_text(out / "r15" / "narrative.csv", r15_narrative.to_csv(data["narrative"]))
