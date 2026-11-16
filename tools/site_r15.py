"""The "Changes from Release 1.5" page: this guide compared with the Release 1.5 baseline (tools/diff_r15.py).

Release 1.5 is represented as NIST's conformance profiles (the source of truth for format and validation, what
systems were tested against) plus the guidance in the 2018 narrative. This page shows the structural comparison;
the narrative comparison is added from quality/r15/ as it is reviewed.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import diff_r15
from guidecards import write_text

NIST_TOOL = "https://tools.valitheus.com/immunization-edition2/#/doc"
CDC_PAGE = "https://www.cdc.gov/iis/technical-guidance/hl7.html"
KIND_LABEL = {"tightened": "Tightened", "loosened": "Loosened", "added": "Added", "removed": "Removed", "changed": "Changed"}
LONG = 12  # code lists longer than this are folded


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def load(repo: Path) -> dict | None:
    if not (repo / "prior" / "release-1.5" / "model" / "profiles.json").exists() or not (repo / "model" / "profiles.json").exists():
        return None
    return diff_r15.compute(repo)


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
<li>{counts.get("usage", 0)} usage changes: {kinds["tightened"]} tightened, {kinds["loosened"]} loosened, the rest changed in other ways</li>
<li>{counts.get("cardinality", 0)} cardinality changes and {counts.get("datatype", 0)} data type changes</li>
<li>{counts.get("binding", 0)} changes to the value sets fields use, and {len(data["code_changes"])} changes to the codes in them</li>
<li>{counts.get("length", 0)} changed lengths; {len(dropped)} elements no longer state a length</li>
</ul>
<p class="mini">Fields and components are compared where either guide constrains them (usage other than O or X);
components are compared two levels deep. A change that is the same in several profiles is shown once.</p>

<h2 id="structure">Message structure</h2>
<table class="r15"><thead><tr><th>Segment or group</th><th>Release 1.5</th><th>This guide</th><th>Profiles</th></tr></thead>
<tbody>{seg_html}</tbody></table>

<h2 id="fields">Fields and components</h2>
<p class="mini">By segment: {seg_index}</p>
{"".join(seg_sections)}

<h2 id="codes">Codes in value sets</h2>
<p>Codes allowed in Release 1.5 and not in this guide (removed), and the reverse (added), for the fields that use each
value set.</p>
<table class="r15"><thead><tr><th>Value set</th><th>Added</th><th>Removed</th><th>Fields</th></tr></thead>
<tbody>{code_html}</tbody></table>

<h2 id="lengths">Lengths</h2>
<p>Release 1.5 states a length for {len(dropped)} elements that this guide does not. Elements whose stated length changed are
listed with the fields above.</p>
<details><summary>Elements that no longer state a length</summary><p class="mini">{len_list}</p></details>

<h2 id="narrative">Guidance in the narrative</h2>
<p class="empty">The comparison of the 2018 narrative with this guide is in progress.</p>
</article>"""


def build_page(out: Path, data: dict, write) -> None:
    """Writes r15/index.html (through write(path, body)) and r15/changes.csv."""
    write(out / "r15" / "index.html", page(data, "../"))
    write_text(out / "r15" / "changes.csv", diff_r15.to_csv(data))
