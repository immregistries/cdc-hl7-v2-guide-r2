#!/usr/bin/env python3
"""Build the guide website from committed content.

    python tools/build_site.py                  # writes output/site/
    python tools/build_site.py --out somewhere

Each card becomes a page at <card-id>/index.html. The left navigation tree is
drawn from assets/nav.js. Quality findings (tools/check_cards.py) appear on the
pages they concern and in the Quality review page. Needs PyYAML only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_cards  # noqa: E402
import minimd  # noqa: E402
import site_igamt  # noqa: E402
from guidecards import CARDS_DIR, DATA_DIR, META, REPO, read_yaml, walk, write_text  # noqa: E402

SITE_SRC = REPO / "site"
SEV_LABEL = {"issue": "Issue", "warning": "Warning", "note": "Note"}
VERB_CLASS = {"SHALL": "shall", "SHALL NOT": "shall-not", "SHOULD": "should", "SHOULD NOT": "should-not",
              "MAY": "may", "MAY NOT": "should-not"}
RULE_HELP = {
    "statement-from-paragraph": "Requirements written as paragraphs in the draft, shown here as conformance statements (wording unchanged).",
    "normative-prose": "Narrative wording such as \"must\" or \"required to\" that reads like a requirement.",
    "no-actor": "Statements that do not name the system or party that must comply.",
    "verb-in-prose": "Explanatory paragraphs that also contain SHALL, SHOULD, or MAY.",
    "statements-mid-section": "Explanation continues after the requirements in the draft; check the order on the card.",
    "image-figure": "Figures stored as images; tables and text inside them cannot be searched or read aloud.",
    "long-card": "Sections longer than the 1–3 paragraph target.",
    "multi-verb-statement": "Statements that combine different conformance verbs.",
    "compound-statement": "Statements that repeat their verb and may hold more than one requirement.",
    "duplicate-title": "Sections that share a title with another section.",
    "no-introduction": "Sections with sub-sections but no introduction of their own.",
    "repeated-text": "Text that appears more than once on the same section.",
    "actor-vocabulary": "Different names used for the same kinds of systems.",
    "empty-card": "Sections with no content.",
    "empty-change-history": "The change history is empty.",
    "figure-numbering": "Gaps and irregularities in figure numbers.",
    "glossary-see-unresolved": "Glossary pointers that do not match a section title.",
    "heading-variants": "One heading spelled more than one way.",
    "long-statement": "Very long statements.",
    "manual": "Found by a reviewer.",
    **site_igamt.RULE_HELP,
}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


# =========================================================================== page shell


def shell(*, root: str, title: str, body: str, guide: dict, build: dict, card_id: str = "", page_class: str = "") -> str:
    status = esc(guide.get("status", "Draft"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(guide['short_title'])}</title>
<link rel="stylesheet" href="{root}assets/tokens.css">
<link rel="stylesheet" href="{root}assets/site.css">
<script>try{{if(localStorage.getItem('guide-hide-findings')==='1')document.documentElement.classList.add('hide-findings')}}catch(e){{}}</script>
</head>
<body class="{page_class}" data-root="{root}" data-card="{esc(card_id)}">
<a class="skip" href="#main">Skip to content</a>
<div class="draft-bar" role="note"><strong>{status.upper()}</strong> · {esc(guide.get('status_note', ''))}</div>
<header class="topbar">
  <button class="tree-toggle" type="button" aria-controls="tree" aria-expanded="false" title="Contents">☰</button>
  <a class="brand" href="{root}index.html">
    <span class="publishers">{' · '.join(esc(p['short']) for p in guide['publishers'])}</span>
    <span class="guide-name">{esc(guide['short_title'])}</span>
  </a>
  <nav class="toplinks" aria-label="Guide">
    <a href="{root}contents/index.html">Contents</a>
    <a href="{root}quality/index.html">Quality review</a>
    <a href="{root}glossary/index.html">Glossary</a>
    <button class="findings-toggle" type="button" aria-pressed="false">Hide findings</button>
  </nav>
</header>
<div class="layout">
  <nav class="tree" id="tree" aria-label="Table of contents">
    <div class="tree-filter"><input type="search" placeholder="Filter sections" aria-label="Filter sections"></div>
    <div class="tree-body"><a href="{root}contents/index.html">Table of contents</a></div>
  </nav>
  <main id="main" tabindex="-1">
{body}
  </main>
</div>
<footer class="site-footer">
  <p><strong>{status.upper()}</strong> — {esc(guide['title'])}, {esc(guide['release'])}. A joint publication of the
  {' and the '.join(esc(p['name']) for p in guide['publishers'])}. {esc(guide.get('status_note', ''))}</p>
  <p class="build">Built {esc(build['date'])} from narrative draft <code>{esc(build['source'])}</code>{esc(build['commit'])}.
  <a href="{esc(guide['repository'])}">Source on GitHub</a>.</p>
</footer>
<dialog class="lightbox" aria-label="Figure"><form method="dialog"><button class="close" aria-label="Close">×</button></form><img alt=""><p class="lb-caption"></p></dialog>
<script src="{root}assets/nav.js"></script>
<script src="{root}assets/site.js"></script>
</body>
</html>
"""


# =========================================================================== fragments


def findings_panel(items: list[dict], root: str, anchors: dict) -> str:
    if not items:
        return ""
    sev = Counter(i["severity"] for i in items)
    summary = " · ".join(f"{sev[s]} {SEV_LABEL[s].lower()}{'s' if sev[s] != 1 else ''}" for s in ("issue", "warning", "note") if sev[s])
    worst = next(s for s in ("issue", "warning", "note") if sev[s])
    lis = []
    for i in sorted(items, key=lambda x: (("issue", "warning", "note").index(x["severity"]), x["id"])):
        where = ""
        loc = i.get("location")
        if loc and loc in anchors:
            where = f' <a class="f-loc" href="#{esc(loc)}">{esc(anchors[loc])}</a>'
        ev = i.get("evidence") or {}
        evidence = ""
        if "text" in ev and not (loc and loc in anchors):
            evidence = f"<blockquote>{esc(ev['text'])}</blockquote>"
        if any(k in ev for k in ("narrative", "xml", "recommendation", "variants")):
            evidence += site_igamt.evidence_html(ev)
        disp = ""
        if i.get("disposition"):
            d = i["disposition"]
            disp = f'<p class="f-disp">Decision: <strong>{esc(d.get("status", ""))}</strong> {esc(d.get("note", ""))}</p>'
        lis.append(
            f'<li class="finding sev-{i["severity"]}" id="{esc(i["id"])}">'
            f'<span class="sev">{SEV_LABEL[i["severity"]]}</span>{where} {esc(i["message"])}{evidence}{disp}'
            f'<a class="f-id" href="{root}quality/index.html#{esc(i["id"])}">{esc(i["id"])}</a></li>'
        )
    return f"""<aside class="findings sev-{worst}" aria-label="Quality review findings">
<details open><summary><span class="f-title">Quality review</span> <span class="f-count">{summary}</span></summary>
<p class="f-help">Findings from automated and editorial checks, for the authors and reviewers. Not part of the guide.</p>
<ul>{''.join(lis)}</ul></details></aside>"""


def statements_html(card, flagged: dict) -> str:
    if not card.statements:
        return ""
    lis = []
    for s in card.statements:
        verb = s.get("verb", "")
        flag = ""
        if s["id"] in flagged:
            sev = flagged[s["id"]]
            flag = f'<a class="s-flag sev-{sev}" href="#findings" title="This statement has a quality finding">⚑</a>'
        short = s["id"].rsplit("--", 1)[-1]
        lis.append(
            f'<li id="{esc(s["id"])}"><span class="verb verb-{VERB_CLASS.get(verb, "may")}">{esc(verb)}</span>'
            f'<span class="s-text">{esc(s["text"])}</span>'
            f'<span class="s-meta">{flag}<a class="s-id" href="#{esc(s["id"])}" title="Link to this statement">{esc(short)}</a></span></li>'
        )
    return f'<section class="statements" aria-labelledby="st-h"><h2 id="st-h">Conformance statements</h2><ol>{"".join(lis)}</ol></section>'


def figures_html(card, root_card: str) -> str:
    figs = card.meta.get("figures", [])
    if not figs:
        return ""
    out = []
    for f in figs:
        label = f"Figure {f['number']}" if f.get("number") is not None else "Figure"
        alt = f.get("alt") or f.get("caption") or label
        out.append(
            f'<figure id="{esc(f["id"])}"><button type="button" class="fig-open" data-src="{esc(f["file"])}" data-caption="{esc(label + ": " + f.get("caption", ""))}">'
            f'<img src="{esc(f["file"])}" alt="{esc(alt)}" loading="lazy"></button>'
            f'<figcaption><strong>{esc(label)}.</strong> {esc(f.get("caption", ""))}</figcaption></figure>'
        )
    return f'<section class="figures" aria-label="Figures">{"".join(out)}</section>'


def tables_html(card) -> str:
    out = []
    for t in card.meta.get("tables", []):
        path = card.path / t["file"]
        if not path.exists():
            continue
        caption = ""
        if t.get("caption"):
            label = f"Figure {t['number']}. " if t.get("number") is not None else ""
            caption = f"<p class='table-caption'><strong>{esc(label)}</strong>{esc(t['caption'])}</p>"
        out.append(f'<div class="table-wrap" id="{esc(t["id"])}">{caption}{minimd.table(path.read_text(encoding="utf-8"))}</div>')
    return "".join(out)


def glossary_html(name: str) -> str:
    data = read_yaml(DATA_DIR / f"{name}.yml", {}) or {}
    out = []
    for g in data.get("groups", []):
        out.append(f"<h3>{esc(g['name'])}</h3><dl class='terms'>")
        for t in g.get("terms", []):
            anchor = "term-" + re.sub(r"[^a-z0-9]+", "-", t["term"].lower()).strip("-")
            out.append(f"<dt id='{anchor}'>{esc(t['term'])}</dt><dd>{minimd.render(t['definition'])}</dd>")
        out.append("</dl>")
    return f'<section class="key-terms">{"".join(out)}</section>' if out else ""


# =========================================================================== build


def git_commit() -> str:
    sha = os.environ.get("GITHUB_SHA")
    if not sha:
        try:
            sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sha = ""
    return f", commit {sha[:7]}" if sha else ""


def build(out: Path) -> dict:
    guide = read_yaml(DATA_DIR / "guide.yml", {})
    source = (read_yaml(CARDS_DIR / META / "source.yml", {}) or {}).get("narrative_docx", {})
    build_info = {
        "date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source.get("file", "unknown"),
        "commit": git_commit(),
    }
    roots, findings, structure = check_cards.run_checks_full(CARDS_DIR, DATA_DIR, REPO / "quality")
    xref = (structure or {}).get("xref", {})
    cards = list(walk(roots))
    by_id = {c.id: c for c in cards}
    by_card = defaultdict(list)
    general = []
    for f in findings:
        (by_card[f["card"]] if f.get("card") in by_id else general).append(f)
    refs = (read_yaml(DATA_DIR / "references.yml", {}) or {}).get("references", [])
    ref_by_num = {r["number"]: r for r in refs}

    out.mkdir(parents=True, exist_ok=True)
    for entry in out.iterdir():  # clear contents (the folder itself may be in use, e.g. by a preview server)
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    (out / "assets").mkdir(parents=True)
    for name in ("tokens.css", "site.css", "site.js"):
        shutil.copy2(SITE_SRC / "theme" / name, out / "assets" / name)

    # ---------------------------------------------------------------- nav data
    def counts(c):
        sev = Counter(f["severity"] for f in by_card.get(c.id, []))
        return [sev["issue"], sev["warning"], sev["note"]]

    def node(c):
        n = {"i": c.id, "t": c.title, "n": c.number, "f": counts(c)}
        if c.children:
            n["c"] = [node(x) for x in c.children]
        return n

    extra = [
        {"i": "structure", "t": "Message Infrastructure", "n": str(len(roots) + 1), "p": "structure/index.html", "f": [0, 0, 0]},
        {"i": "examples", "t": "Example Messages", "n": "A", "p": "examples/index.html", "f": [0, 0, 0]},
        {"i": "glossary", "t": "Glossary and Abbreviations", "n": "B", "p": "glossary/index.html", "f": [0, 0, 0]},
        {"i": "resources", "t": "Resources", "n": "C", "p": "resources/index.html", "f": [0, 0, 0]},
        {"i": "quality", "t": "Quality Review", "n": "", "p": "quality/index.html",
         "f": [sum(f["severity"] == s for f in findings) for s in ("issue", "warning", "note")]},
    ]
    if structure:
        cmp_f = [f for f in findings if f["category"] in ("igamt", "igamt-export")]
        extra.append({"i": "quality-igamt", "t": "Narrative vs IGAMT", "n": "", "p": "quality/igamt/index.html",
                      "f": [sum(f["severity"] == s for f in cmp_f) for s in ("issue", "warning", "note")]})
    nav = {"nodes": [node(r) for r in roots], "extra": extra}
    write_text(out / "assets" / "nav.js", "window.GUIDE_NAV=" + json.dumps(nav, ensure_ascii=False, separators=(",", ":")) + ";\n")

    # ---------------------------------------------------------------- card pages
    order = cards
    for idx, c in enumerate(order):
        root = "../"
        page_dir = out / c.id
        page_dir.mkdir(parents=True, exist_ok=True)
        for f in c.meta.get("figures", []):
            shutil.copy2(c.path / f["file"], page_dir / f["file"])
        crumbs = []
        p = c.parent
        while p is not None:
            crumbs.insert(0, f'<a href="{root}{p.id}/index.html">{esc(p.number)} {esc(p.title)}</a>')
            p = p.parent
        crumbs.insert(0, f'<a href="{root}index.html">Home</a>')
        items = by_card.get(c.id, [])
        anchors = {s["id"]: "Statement " + s["id"].rsplit("--", 1)[-1] for s in c.statements}
        anchors.update({f["id"]: (f"Figure {f['number']}" if f.get("number") is not None else "Figure") for f in c.meta.get("figures", [])})
        flagged = {}
        for f in items:
            if f.get("location") in anchors and f.get("location", "").count("--"):
                cur = flagged.get(f["location"])
                if cur is None or ("issue", "warning", "note").index(f["severity"]) < ("issue", "warning", "note").index(cur):
                    flagged[f["location"]] = f["severity"]
        refs_cited = [ref_by_num[n] for n in c.meta.get("references", []) if n in ref_by_num]
        refs_html = ""
        if refs_cited:
            lis = "".join(
                f'<li><a href="{root}resources/index.html#ref-{r["number"]}">[{r["number"]}]</a> '
                + (f'<a href="{esc(r["url"])}" rel="noopener" target="_blank">{esc(r["title"])}</a>' if r.get("url") else esc(r["title"]))
                + "</li>" for r in refs_cited)
            refs_html = f'<section class="related"><h2>Resources cited</h2><ul>{lis}</ul></section>'
        children_html = ""
        if c.children:
            lis = "".join(
                f'<li><a href="{root}{k.id}/index.html"><span class="num">{esc(k.number)}</span> {esc(k.title)}</a>'
                + (f' <span class="mini">{len(k.statements)} statement{"s" if len(k.statements) != 1 else ""}</span>' if k.statements else "")
                + "</li>" for k in c.children)
            children_html = f'<section class="children"><h2>In this section</h2><ol>{lis}</ol></section>'
        prev_c = order[idx - 1] if idx > 0 else None
        next_c = order[idx + 1] if idx + 1 < len(order) else None
        pager = '<nav class="pager" aria-label="Previous and next">'
        pager += (f'<a class="prev" href="{root}{prev_c.id}/index.html"><span>Previous</span>{esc(prev_c.number)} {esc(prev_c.title)}</a>'
                  if prev_c else '<span></span>')
        pager += (f'<a class="next" href="{root}{next_c.id}/index.html"><span>Next</span>{esc(next_c.number)} {esc(next_c.title)}</a>'
                  if next_c else f'<a class="next" href="{root}structure/index.html"><span>Next</span>Message Infrastructure</a>')
        pager += "</nav>"
        narrative = minimd.render(c.narrative, citation_href=f"{root}resources/index.html") if c.narrative.strip() else ""
        empty = "" if (narrative or c.statements or c.children or c.meta.get("figures") or c.meta.get("glossary")) \
            else '<p class="empty">This section has no content in the current draft.</p>'
        body = f"""<article class="card" id="card">
<nav class="crumbs" aria-label="Breadcrumb">{' <span>›</span> '.join(crumbs)}</nav>
<header class="card-head"><h1><span class="num">{esc(c.number)}</span> {esc(c.title)}</h1>
<button type="button" class="permalink" data-copy="" title="Copy the permanent link to this section">Copy link</button></header>
{findings_panel(items, root, anchors)}
<div class="narrative">{narrative}{empty}</div>
{glossary_html(c.meta['glossary']) if c.meta.get('glossary') else ''}
{statements_html(c, flagged)}
{site_igamt.structure_panel(xref.get(c.id, []), root)}
{figures_html(c, root)}
{tables_html(c)}
{refs_html}
{children_html}
{pager}
</article>"""
        write_text(page_dir / "index.html", shell(root=root, title=f"{c.number} {c.title}", body=body, guide=guide,
                                                  build=build_info, card_id=c.id, page_class="card-page"))

    # ---------------------------------------------------------------- landing
    sev_all = Counter(f["severity"] for f in findings)
    chapters = []
    for r in roots:
        n_cards = sum(1 for _ in r.walk())
        n_st = sum(len(x.statements) for x in r.walk())
        first = re.split(r"(?<=[.!?])\s", re.sub(r"[*\\]", "", r.narrative.strip()), maxsplit=1)[0] if r.narrative.strip() else ""
        chapters.append(f'<li><a href="{r.id}/index.html"><span class="num">{esc(r.number)}</span> {esc(r.title)}</a>'
                        f'<p>{esc(first)}</p><p class="mini">{n_cards} sections · {n_st} conformance statements</p></li>')
    chapters.append(f'<li><a href="structure/index.html"><span class="num">{len(roots) + 1}</span> Message Infrastructure</a>'
                    '<p>Message profiles, segments, data types, and value sets, generated from the IGAMT conformance export.</p><p class="mini">Coming next</p></li>')
    total_st = sum(len(c.statements) for c in cards)
    landing = f"""<section class="hero">
<p class="eyebrow">{esc(guide['release'])} · {esc(guide['status'])}</p>
<h1>{esc(guide['title'])}</h1>
<p class="publishers-line">A joint publication of the {' and the '.join(esc(p['name']) for p in guide['publishers'])}</p>
<div class="intro">{minimd.render(guide.get('intro', ''))}</div>
<p><a class="button" href="{roots[0].id}/index.html">Start reading</a> <a class="button secondary" href="contents/index.html">Table of contents</a></p>
<p class="stats">{len(cards)} sections · {total_st} conformance statements · <a href="quality/index.html">{len(findings)} quality findings</a>
({sev_all['issue']} issues, {sev_all['warning']} warnings, {sev_all['note']} notes)</p>
</section>
<section class="chapters"><h2>Chapters</h2><ol class="chapter-list">{''.join(chapters)}</ol></section>"""
    write_text(out / "index.html", shell(root="", title="Home", body=landing, guide=guide, build=build_info, page_class="home"))

    # ---------------------------------------------------------------- contents
    def toc(nodes):
        lis = []
        for c in nodes:
            meta = f' <span class="mini">{len(c.statements)} S</span>' if c.statements else ""
            sub = f"<ol>{toc(c.children)}</ol>" if c.children else ""
            lis.append(f'<li><a href="../{c.id}/index.html"><span class="num">{esc(c.number)}</span> {esc(c.title)}</a>{meta}{sub}</li>')
        return "".join(lis)

    contents = f"""<article class="page"><h1>Table of contents</h1>
<ol class="toc">{toc(roots)}
<li><a href="../structure/index.html"><span class="num">{len(roots) + 1}</span> Message Infrastructure</a> <span class="mini">coming</span></li>
<li><a href="../examples/index.html"><span class="num">A</span> Example Messages</a> <span class="mini">coming</span></li>
<li><a href="../glossary/index.html"><span class="num">B</span> Glossary and Abbreviations</a></li>
<li><a href="../resources/index.html"><span class="num">C</span> Resources</a></li></ol></article>"""
    write_text(out / "contents" / "index.html", shell(root="../", title="Contents", body=contents, guide=guide, build=build_info))

    # ---------------------------------------------------------------- quality
    by_rule = Counter(f["rule"] for f in findings)
    rule_sev = {}
    for f in findings:
        rule_sev.setdefault(f["rule"], Counter())[f["severity"]] += 1
    rows = "".join(
        f'<tr><td><a href="#rule-{esc(r)}"><code>{esc(r)}</code></a></td><td>{esc(RULE_HELP.get(r, ""))}</td>'
        f'<td class="n">{n}</td></tr>' for r, n in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0])))
    sections = []
    for rule, n in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0])):
        lis = []
        for f in sorted((x for x in findings if x["rule"] == rule),
                        key=lambda x: (("issue", "warning", "note").index(x["severity"]),
                                       [int(p) if p.isdigit() else 0 for p in by_id[x["card"]].number.split(".")] if x.get("card") in by_id else [], x["id"])):
            where = ""
            if f.get("card") in by_id:
                c = by_id[f["card"]]
                target = f"../{c.id}/index.html" + (f"#{f['location']}" if f.get("location") and "--" in f["location"] else f"#{f['id']}")
                where = f'<a href="{target}">{esc(c.number)} {esc(c.title)}</a>: '
            ev = f.get("evidence") or {}
            extra_ev = ""
            if "actors" in ev:
                extra_ev = "<p class='mini'>" + esc("; ".join(f"{k} ({v})" for k, v in ev["actors"].items())) + "</p>"
            elif "text" in ev:
                extra_ev = f"<blockquote>{esc(ev['text'])}</blockquote>"
            if any(k in ev for k in ("narrative", "xml", "recommendation", "variants")):
                extra_ev += site_igamt.evidence_html(ev)
            if not where and (f.get("location") or "").startswith("model:"):
                where = f'<code class="mini">{esc(f["location"][6:])}</code> '
            lis.append(f'<li class="finding sev-{f["severity"]}" id="{esc(f["id"])}"><span class="sev">{SEV_LABEL[f["severity"]]}</span> '
                       f'{where}{esc(f["message"])}{extra_ev}<span class="f-id">{esc(f["id"])}</span></li>')
        sections.append(f'<section id="rule-{esc(rule)}"><h2><code>{esc(rule)}</code> <span class="mini">{n}</span></h2>'
                        f'<p>{esc(RULE_HELP.get(rule, ""))}</p><details{" open" if n <= 12 else ""}><summary>Show {n} finding{"s" if n != 1 else ""}</summary>'
                        f'<ul class="finding-list">{"".join(lis)}</ul></details></section>')
    quality = f"""<article class="page quality"><h1>Quality review</h1>
<p>These findings come from automated checks run on every build, and from editorial review. They point to places where the
draft may be unclear, inconsistent, or hard to use, for the authors to consider. Each finding has a permanent ID, and it
also appears on the section it concerns. Checks for duplication across sections and for example messages will be added in
later builds.</p>
<p class="callout"><a href="igamt/index.html"><strong>Narrative and IGAMT structure comparison</strong></a>: does the text
match the conformance profiles? Answers to the Word review comments, conflicts, change requests for IGAMT, and decisions for CDC.
<a href="findings.csv">Download all findings (CSV)</a>.</p>
<p class="stats">{len(findings)} findings: {sev_all['issue']} issues, {sev_all['warning']} warnings, {sev_all['note']} notes.</p>
<table class="rules"><thead><tr><th>Check</th><th>What it looks for</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table>
{''.join(sections)}</article>"""
    write_text(out / "quality" / "index.html", shell(root="../", title="Quality review", body=quality, guide=guide, build=build_info))
    write_text(out / "quality" / "findings.csv", site_igamt.findings_csv(findings, by_id, guide.get("site", "")))
    if structure:
        model_src = read_yaml(REPO / "model" / "source.yml", {}) or {}
        page = site_igamt.comparison_page(structure, findings, by_id, "../../",
                                          {"narrative": build_info["source"], "igamt": model_src.get("export", "unknown")})
        write_text(out / "quality" / "igamt" / "index.html",
                   shell(root="../../", title="Narrative and IGAMT comparison", body=page, guide=guide, build=build_info))

    # ---------------------------------------------------------------- glossary and resources
    gl = read_yaml(DATA_DIR / "glossary.yml", {}) or {}
    parts = [f"<article class='page'><h1>Glossary and Abbreviations</h1>{minimd.render(gl.get('intro', ''))}"]
    for g in gl.get("groups", []):
        parts.append(f"<h2>{esc(g['name'])}</h2><dl class='terms'>")
        for e in g.get("entries", []):
            anchor = "term-" + re.sub(r"[^a-z0-9]+", "-", e["term"].lower()).strip("-")
            parts.append(f"<dt id='{anchor}'>{esc(e['term'])}</dt><dd>{minimd.render(e['definition'])}</dd>")
        parts.append("</dl>")
    parts.append("</article>")
    write_text(out / "glossary" / "index.html", shell(root="../", title="Glossary", body="".join(parts), guide=guide, build=build_info))

    rd = read_yaml(DATA_DIR / "references.yml", {}) or {}
    lis, current_group = [], None
    for r in rd.get("references", []):
        if r.get("group") != current_group:
            current_group = r.get("group")
            g = next((x for x in rd.get("groups", []) if x["name"] == current_group), {})
            lis.append(f"</ol><h2>{esc(current_group)}</h2><p>{esc(g.get('description', ''))}</p><ol class='refs'>")
        title = f'<a href="{esc(r["url"])}" rel="noopener" target="_blank">{esc(r["title"])}</a>' if r.get("url") else esc(r["title"])
        lis.append(f'<li id="ref-{r["number"]}" value="{r["number"]}">{title}<p>{esc(r.get("description", ""))}</p></li>')
    resources = f"<article class='page'><h1>Resources</h1>{minimd.render(rd.get('intro', ''))}<ol class='refs'>{''.join(lis)}</ol></article>"
    write_text(out / "resources" / "index.html", shell(root="../", title="Resources", body=resources, guide=guide, build=build_info))

    # ---------------------------------------------------------------- placeholders
    write_text(out / "structure" / "index.html", shell(root="../", title="Message Infrastructure", guide=guide, build=build_info, body=f"""
<article class="page"><h1><span class="num">{len(roots) + 1}</span> Message Infrastructure</h1>
<p>This chapter is generated from the IGAMT conformance export: the eight message profiles (Z22, Z23, Z31, Z32, Z33, Z34,
Z42, Z44), their segments and fields, data types, value sets, conformance statements, and co-constraints. Each profile,
segment, data type, and value set will have its own page, linked from the sections that discuss it.</p>
<p class="empty">Coming in the next build.</p></article>"""))
    write_text(out / "examples" / "index.html", shell(root="../", title="Example Messages", guide=guide, build=build_info, body="""
<article class="page"><h1><span class="num">A</span> Example Messages</h1>
<p>Complete, validated example messages will appear on the sections they illustrate and be listed here, with the part
of each message that a section discusses highlighted.</p><p class="empty">Coming in a later build.</p></article>"""))

    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {"cards": len(cards), "findings": len(findings), "out": out}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=REPO / "output" / "site")
    args = parser.parse_args(argv)
    result = build(args.out)
    print(f"Built {result['cards']} card pages with {result['findings']} findings: {result['out'] / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
