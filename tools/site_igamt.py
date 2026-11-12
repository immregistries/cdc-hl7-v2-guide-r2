"""Site fragments and the comparison page for the narrative ↔ IGAMT review (used by build_site.py)."""

from __future__ import annotations

import csv
import html
import io
from collections import Counter

SEV_ORDER = ("issue", "warning", "note")
SEV_LABEL = {"issue": "Issue", "warning": "Warning", "note": "Note"}
KIND_LABEL = {
    "conflict": "Conflict", "gap": "Gap", "xml-defect": "IGAMT export defect", "narrative-defect": "Narrative defect",
    "question": "Question", "confirmed": "Confirmed",
}
OWNER_LABEL = {"narrative": "Narrative", "igamt": "IGAMT", "both": "Narrative and IGAMT", "decision": "CDC decision"}
RULE_HELP = {
    "igamt-review": "Reviewed comparison of the narrative with the IGAMT conformance export.",
    "xml-figure-cocon": "Figure 20 (Order Segment Group flavors) compared cell by cell with the OBX co-constraint tables.",
    "xml-field-name": "Field names in the text that differ from the HL7 names in the profiles.",
    "xml-unknown-field": "Field references that do not exist in the profiles.",
    "xml-unknown-segment": "Segment references not used by any profile.",
    "xml-code-not-bound": "Codes used in the text that are not in the value set bound to the field.",
    "igamt-c-no-predicate": "Conditional (C) usage without a predicate in a constrained flavor.",
    "igamt-c-no-predicate-base": "Conditional usage without a predicate in base segments and data types.",
    "igamt-placeholder-binding": "Co-constraint bindings to a placeholder-only value set.",
    "igamt-placeholder-value-set": "HL7 user-defined tables that hold only a placeholder.",
    "igamt-empty-value-set": "Bound value sets with no codes.",
    "igamt-missing-value-set": "Bindings to value sets that are not defined.",
    "igamt-code-no-usage": "Codes without a usage (R/P/E) in a value set.",
    "igamt-constraint-id-reuse": "Conformance statement IDs used with different wordings.",
    "igamt-constraint-no-strength": "Generated constraints without a strength.",
    "igamt-cocon-duplicate-row": "Repeated rows in a co-constraint table.",
    "igamt-cocon-type-mismatch": "One LOINC with different OBX-2 value types across co-constraint tables.",
    "igamt-cocon-binding-mismatch": "One LOINC with different OBX-5 value sets across co-constraint tables.",
    "igamt-cocon-usage": "Co-constraint usage codes the guide does not define.",
    "igamt-datatype-duplicate": "Data types defined more than once.",
    "igamt-unused-flavor": "Segment flavors not used by any message.",
    "igamt-profile-name": "Inconsistent profile names.",
    "igamt-metadata": "Missing version and date in the export.",
    "example-cocon": "Example observations (OBX) that the co-constraint tables do not allow, or with the wrong value type or value set.",
    "example-cocon-missing": "Example order groups missing an observation the co-constraint tables require.",
    "example-required": "Required fields or components that are empty in an example.",
    "example-not-supported": "Fields or components marked X (not supported) that an example values.",
    "example-cardinality": "Fields in an example with more repetitions than the profile allows.",
    "example-code": "Codes in an example that are not in a closed value set bound to the field.",
    "example-code-open": "Codes in an example that are not in an open value set bound to the field.",
    "example-format": "Dates and times in an example that do not match the data type's format.",
    "example-constraint": "Example segments that fail a conformance statement of their flavor.",
    "example-structure": "Example segments the profile does not include or support, or required segments that are missing.",
    "example-message-type": "Examples whose MSH-9 does not match their profile.",
    "example-profile": "Examples whose MSH-21 does not name a known profile.",
    "example-needs-input": "Examples marked Question or Need help in CDC's example list.",
    "example-missing": "Examples requested in CDC's list that are not drafted yet.",
    "example-section-unresolved": "Example list entries that name a sub-section the narrative does not have.",
}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------- card fragments

def structure_panel(items: list[dict], root: str, st=None) -> str:
    """What the profiles say about the fields a card mentions."""
    if not items:
        return ""
    rows = []
    for it in items:
        usage = "".join(f'<div class="u-row"><span class="u">{esc(u["usage"])}</span> <span class="u-where">{esc(u["where"])}</span></div>'
                        for u in it["usage"])
        vs = ", ".join((st.vs_link(v, root) if st else f"<code>{esc(v)}</code>") for v in it["value_sets"]) or '<span class="mini">—</span>'
        seg, pos = it["ref"].split("-")
        ref = (f'<a href="{st.segment_href(seg, root, int(pos))}"><code>{esc(it["ref"])}</code></a>' if st else f"<code>{esc(it['ref'])}</code>")
        cs = " ".join(f'<abbr class="cs" title="{esc(c["context"] + ": " + c["description"])}">{esc(c["id"])}</abbr>' for c in it["constraints"])
        rows.append(f'<tr><th scope="row">{ref}<div class="mini">{esc(it["name"] or "")}</div></th>'
                    f'<td>{usage}</td><td>{vs}</td><td>{cs or "<span class=mini>—</span>"}</td></tr>')
    return f"""<section class="xref" aria-labelledby="xref-h"><details>
<summary><h2 id="xref-h">Message structure for the fields on this page</h2> <span class="mini">{len(items)} field{'s' if len(items) != 1 else ''} · from the IGAMT export</span></summary>
<p class="mini">Usage, cardinality, and data type of each field in each message profile, the value sets that govern its code, and the
conformance statements that test it. <a href="{root}quality/igamt/index.html">How the narrative compares with these profiles</a>.</p>
<div class="table-wrap"><table class="xref-table"><thead><tr><th>Field</th><th>Usage [cardinality] data type: where</th><th>Value sets</th><th>Constraints</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></details></section>"""


def evidence_html(ev: dict) -> str:
    """Narrative / XML / recommendation evidence of a reviewed finding."""
    parts = []
    if ev.get("narrative"):
        parts.append(f'<div class="ev"><span class="ev-k">Narrative</span> {esc(ev["narrative"])}</div>')
    xml = ev.get("xml")
    if isinstance(xml, list) and xml:
        parts.append('<div class="ev"><span class="ev-k">IGAMT export</span><ul>' + "".join(f"<li>{esc(x)}</li>" for x in xml) + "</ul></div>")
    elif isinstance(xml, str):
        parts.append(f'<div class="ev"><span class="ev-k">IGAMT export</span> {esc(xml)}</div>')
    if ev.get("variants"):
        parts.append('<div class="ev"><span class="ev-k">Wordings</span><ul>' + "".join(f"<li>{esc(x)}</li>" for x in ev["variants"]) + "</ul></div>")
    if ev.get("recommendation"):
        parts.append(f'<div class="ev"><span class="ev-k">Recommendation</span> {esc(ev["recommendation"])}</div>')
    tags = []
    if ev.get("kind"):
        tags.append(KIND_LABEL.get(ev["kind"], ev["kind"]))
    if ev.get("owner"):
        tags.append("Action: " + OWNER_LABEL.get(ev["owner"], ev["owner"]))
    if ev.get("comment"):
        tags.append(f"Answers Word comment {ev['comment']}")
    if tags:
        parts.insert(0, '<div class="ev-tags">' + "".join(f"<span>{esc(t)}</span>" for t in tags) + "</div>")
    return f'<div class="evidence">{"".join(parts)}</div>' if parts else ""


# ---------------------------------------------------------------- comparison page

def _card_link(card_id, by_id, root, anchor=None) -> str:
    c = by_id.get(card_id)
    if not c:
        return ""
    href = f"{root}{c.id}/index.html" + (f"#{anchor}" if anchor else "")
    return f'<a href="{href}">{esc(c.number)} {esc(c.title)}</a>'


def _finding_li(f: dict, by_id, root) -> str:
    loc = f.get("location") or ""
    where = _card_link(f.get("card"), by_id, root, loc if "--" in loc or loc.startswith("fig-") else f["id"])
    where = f"{where}: " if where else (f'<code class="mini">{esc(loc.replace("model:", ""))}</code> ' if loc.startswith("model:") else "")
    return (f'<li class="finding sev-{f["severity"]}" id="{esc(f["id"])}"><span class="sev">{SEV_LABEL[f["severity"]]}</span> '
            f'{where}{esc(f["message"])}{evidence_html(f.get("evidence") or {})}<span class="f-id">{esc(f["id"])}</span></li>')


def figure_table(matrix: dict, by_id, root) -> str:
    cols = matrix["columns"]
    head = "".join(f"<th>{esc(c['label'])}</th>" for c in cols)
    body = []
    for row in matrix["rows"]:
        tds = []
        for cell in row["cells"]:
            xml = "".join(f'<div class="cc-x"><span class="cc-l">{esc(x["label"])}</span> <b>{esc(x["value"])}</b></div>' for x in cell["xml"])
            cls = "cc-bad" if cell["mismatch"] else "cc-ok"
            tds.append(f'<td class="{cls}"><div class="cc-fig">Figure: <b>{esc(cell["figure"])}</b></div>{xml}</td>')
        body.append(f'<tr><th scope="row">{esc(row["label"])}<div class="mini">{esc(row["loinc"])}</div></th>{"".join(tds)}</tr>')
    link = _card_link(matrix["card"], by_id, root, matrix["figure"])
    return f"""<p>Figure 20 on {link} says which LOINC-coded observations belong in each Order Segment Group flavor
(R required, O optional, – not applicable). Each cell shows the figure's mark and what the co-constraint tables allow in the matching
table: R required, O optional, S (usage 'S', see below), – not allowed. Cells where they disagree are highlighted.</p>
<div class="table-wrap"><table class="cc-matrix"><thead><tr><th>Observation</th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"""


def comparison_page(structure: dict, findings: list[dict], by_id: dict, root: str, source: dict) -> str:
    review = structure["review"]
    st = structure["stats"]
    cmp = [f for f in findings if f["category"] in ("igamt", "igamt-export")]
    rev_f = [f for f in cmp if f["rule"] == "igamt-review"]
    auto_n = [f for f in cmp if f["category"] == "igamt" and f["rule"] != "igamt-review"]
    export_f = [f for f in cmp if f["category"] == "igamt-export"]
    sev = Counter(f["severity"] for f in cmp)
    rev_by_id = {f["id"]: f for f in rev_f}

    def sort_key(f):
        return (SEV_ORDER.index(f["severity"]), f["id"])

    # answers to Word comments
    answers = [r for r in review if r.get("comment")]
    ans_rows = "".join(
        f'<tr><td class="n">{esc(r["comment"])}</td><td>{_card_link(r.get("card"), by_id, root)}</td>'
        f'<td><a href="#{esc(r["id"])}">{esc(r["title"])}</a></td>'
        f'<td>{esc(KIND_LABEL.get(r.get("kind"), r.get("kind", "")))}</td></tr>'
        for r in sorted(answers, key=lambda r: int(r["comment"])))

    # reviewed, grouped by owner
    groups = []
    for owner in ("decision", "both", "igamt", "narrative"):
        items = sorted((rev_by_id[r["id"]] for r in review if r.get("owner") == owner and r["id"] in rev_by_id), key=sort_key)
        if items:
            groups.append(f'<h3>{esc(OWNER_LABEL[owner])} <span class="mini">{len(items)}</span></h3>'
                          f'<ul class="finding-list">{"".join(_finding_li(f, by_id, root) for f in items)}</ul>')

    confirmed = [r for r in review if r.get("kind") == "confirmed"]
    conf_lis = "".join(f'<li id="{esc(r["id"])}">{_card_link(r.get("card"), by_id, root, r.get("location"))}: {esc(r["title"])}'
                       + (f'<div class="mini">{esc(" ".join(r["summary"].split()))}</div>' if r.get("summary") else "") + "</li>"
                       for r in confirmed)
    codes = structure.get("codes_confirmed", [])
    seen, code_lis = set(), []
    for c in codes:
        k = (c["ref"], c["code"])
        if k in seen:
            continue
        seen.add(k)
        code_lis.append(f"<li><code>{esc(c['ref'])}</code> '{esc(c['code'])}' is in <code>{esc(c['value_set'])}</code>"
                        + (f" (usage {esc(c['usage'])})" if c.get("usage") else " (no usage)") + "</li>")

    # change requests for IGAMT = reviewed (igamt/both) + export findings
    cr = sorted([rev_by_id[r["id"]] for r in review if r.get("owner") in ("igamt", "both") and r["id"] in rev_by_id], key=sort_key) \
        + sorted(export_f, key=sort_key)
    cr_rows = "".join(
        f'<tr><td class="n">{i}</td><td><span class="sev-chip sev-{f["severity"]}">{SEV_LABEL[f["severity"]]}</span></td>'
        f'<td>{esc(f["message"].split(". ")[0].rstrip("."))}.'
        + (f'<div class="mini">{esc((f.get("evidence") or {}).get("recommendation", ""))}</div>' if (f.get("evidence") or {}).get("recommendation") else "")
        + f'</td><td><a href="#{esc(f["id"])}" class="mini">{esc(f["id"])}</a></td></tr>'
        for i, f in enumerate(cr, 1))

    fig = figure_table(structure["figure_20"], by_id, root) if structure.get("figure_20") else ""
    profiles = ", ".join(f"{p['code']} ({p['type']})" for p in structure.get("profiles", []))
    auto_lis = "".join(_finding_li(f, by_id, root) for f in sorted(auto_n, key=lambda f: (f["rule"], ) + sort_key(f)))
    export_lis = "".join(_finding_li(f, by_id, root) for f in sorted(export_f, key=sort_key))

    return f"""<article class="page quality igamt-report">
<p class="eyebrow">Quality review</p>
<h1>Narrative and IGAMT structure comparison</h1>
<p class="callout"><strong>For CDC review.</strong> These findings come from automated checks and from an AIRA reviewer's reading of the
export. Each one needs to be verified by CDC before anything is changed in the narrative or in IGAMT; the decisions can be recorded
against the finding IDs.</p>
<p class="lede">Does what the narrative says about messages, fields, codes, and observations match the conformance profiles authored in
IGAMT? This page compares the two, answers the review comments in the Word draft that asked for this check, and lists what
needs to change in IGAMT, in the narrative, or by CDC decision.</p>
<div class="summary-grid">
  <div><b>{sev['issue']}</b><span>issues</span></div>
  <div><b>{sev['warning']}</b><span>warnings</span></div>
  <div><b>{sev['note']}</b><span>notes</span></div>
  <div><b>{len(confirmed)}</b><span>confirmed matches</span></div>
</div>
<p class="mini">Compared: narrative draft <code>{esc(source.get('narrative', ''))}</code> and the IGAMT validation export of
{esc(source.get('igamt', ''))} ({st['profiles']} profiles: {esc(profiles)}; {st['constraints']} conformance statements under
{st['constraint_ids']} IDs; {st['cocon_tables']} co-constraint tables; {st['value_sets']} value sets). The narrative mentions
{st['fields']} distinct fields {st['field_mentions']} times, on {st['cards_with_fields']} sections. All findings are also in
<a href="../findings.csv">findings.csv</a> and on the sections they concern.</p>

<nav class="page-toc" aria-label="On this page"><ol>
<li><a href="#answers">Answers to the Word review comments</a></li>
<li><a href="#reviewed">Reviewed findings, by who acts</a></li>
<li><a href="#figure-20">Figure 20 and the co-constraint tables</a></li>
<li><a href="#change-requests">Change requests for IGAMT</a></li>
<li><a href="#automated">Automated text checks</a></li>
<li><a href="#export">IGAMT export checks</a></li>
<li><a href="#confirmed">What matches</a></li>
<li><a href="#method">How this was done</a></li>
</ol></nav>

<section id="answers"><h2>Answers to the Word review comments</h2>
<p>Several comments in the Word draft ask for a check against the co-constraint tables, slicing, conformance statements, or
value sets. Each is answered by a finding below.</p>
<div class="table-wrap"><table><thead><tr><th>Comment</th><th>Section</th><th>Answer</th><th>Result</th></tr></thead><tbody>{ans_rows}</tbody></table></div>
</section>

<section id="reviewed"><h2>Reviewed findings, by who acts</h2>
<p>Each finding quotes the narrative, cites the export, and recommends a change. <b>CDC decision</b>: the text and the profiles
disagree on intent. <b>Narrative and IGAMT</b>: both need edits. <b>IGAMT</b>: the profiles need to change; the text is right.
<b>Narrative</b>: the text needs to change.</p>
{''.join(groups)}
</section>

<section id="figure-20"><h2>Figure 20 and the co-constraint tables</h2>
{fig}
</section>

<section id="change-requests"><h2>Change requests for IGAMT</h2>
<p>IGAMT remains the source of the message structure, so these changes are made there and come back in the next export. The list
combines reviewed findings with the checks of the export itself, most severe first.</p>
<div class="table-wrap"><table class="cr"><thead><tr><th>#</th><th>Severity</th><th>Change</th><th>Finding</th></tr></thead><tbody>{cr_rows}</tbody></table></div>
</section>

<section id="automated"><h2>Automated text checks</h2>
<p>Run on every build: field references that do not exist, field names that differ from the profiles, codes not in the bound
value sets, and Figure 20 compared with the co-constraint tables.</p>
<ul class="finding-list">{auto_lis or '<li class="mini">None.</li>'}</ul>
</section>

<section id="export"><h2>IGAMT export checks</h2>
<p>Problems in the export itself, independent of the narrative.</p>
<ul class="finding-list">{export_lis}</ul>
</section>

<section id="confirmed"><h2>What matches</h2>
<ul class="confirmed">{conf_lis}</ul>
<h3>Codes used in the text that are in the bound value set</h3>
<ul class="confirmed codes">{''.join(code_lis)}</ul>
</section>

<section id="method"><h2>How this was done</h2>
<ol>
<li>The IGAMT export (NIST validation format) is converted to a normalized model (<code>model/</code> in the repository) by
<code>tools/import_igamt.py</code>. Nothing is edited by hand; IGAMT stays authoritative.</li>
<li>Every field reference in the narrative and statements (for example RXA-20 or PID-5.7) is looked up in every profile and
flavor, including the RXA and PID slices. The automated checks run on every build (<code>tools/compare_structure.py</code>).</li>
<li>Requirements that mention a field, code, observation, or value set were read against the usage, predicates, bindings,
constraints, slicing, and co-constraint tables. The judgements are recorded, with evidence, in
<code>quality/igamt-review.yml</code>, so they can be discussed and revised.</li>
<li>Figure 20 was transcribed (<code>quality/transcriptions/fig-20.yml</code>) and compared cell by cell with the OBX co-constraint tables.</li>
</ol>
<p>Not yet compared: field-level definition texts (not in the export), the example messages, and figures other than Figure 20.</p>
</section>
</article>"""


def findings_csv(findings: list[dict], by_id: dict, base_url: str) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "severity", "category", "rule", "section", "section_title", "url", "location", "message",
                "kind", "action_by", "word_comment", "recommendation", "decision"])
    for f in sorted(findings, key=lambda f: (f["category"], SEV_ORDER.index(f["severity"]), f["id"])):
        c = by_id.get(f.get("card"))
        ev = f.get("evidence") or {}
        url = f"{base_url}{c.id}/" if c else f"{base_url}quality/"
        w.writerow([f["id"], f["severity"], f["category"], f["rule"], c.number if c else "", c.title if c else "", url,
                    f.get("location") or "", f["message"], ev.get("kind", ""), OWNER_LABEL.get(ev.get("owner"), ev.get("owner", "")),
                    ev.get("comment", ""), ev.get("recommendation", ""), (f.get("disposition") or {}).get("status", "")])
    return buf.getvalue()


def review_targets(structure: dict) -> list[dict]:
    """Comment targets on the comparison page: the page, then each reviewed finding (so CDC can respond per finding)."""
    out = [{"i": 0, "label": "Whole page"}]
    for n, r in enumerate([r for r in structure.get("review", []) if r.get("kind") != "confirmed"], 1):
        out.append({"i": n, "label": f"{r['id']}: {r['title']}"[:110], "snippet": r["id"]})
    return out
