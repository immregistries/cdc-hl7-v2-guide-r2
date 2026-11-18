"""TA Questions: can the guide answer what implementers have asked in technical assistance (TA)?

A working analysis for the authors, shown in the author view only (tools/view.py) and left out of a release. The
questions are consolidated from AIRA's TA records outside this repository and published into quality/ta/ by
tools/import_ta.py, which leaves out who asked (jurisdictions, IIS vendors, people) and the individual records:

    quality/ta/index.yml           the pages, in order (generated)
    quality/ta/pages/<page>.yml    the questions on a page, each with its consolidated answer (generated)
    quality/ta/assess/<page>.yml   how well the guide answers each question (written by hand, keyed by question id)

The analysis is about the guide, not the past answers: each question gets a result saying whether the current guide
answers it. Past answers are shown as given, conflicts included, so the authors can copy them in or correct them.
Questions are grouped by segment and field, then by topic. Questions about the Simple Message Mover (SMM) are left out.

- load():        reads the pages and assessments, and checks that every guide reference exists (None if there is no data)
- findings():    questions the guide does not fully answer, as quality findings (category "ta")
- build_pages(): writes ta/index.html and ta/<page>/index.html
- card_panel():  the questions that cite a section
"""

from __future__ import annotations

import html
from collections import Counter
from pathlib import Path

import minimd
from guidecards import read_yaml
from tab_review import _guide_link, _ref_card

KEY = "ta"
OUT_DIR = "ta"
TITLE = "TA Questions"
RULE = "ta-review"
RULE_HELP = ("A question asked in technical assistance that the current guide does not fully answer "
             "(working analysis, local builds only).")

RESULTS = {  # result: (label, default severity, CSS class shared with the TAB comparison, help)
    "answers": ("Answers", None, "r-covered", "The guide answers the question directly."),
    "appeal": ("By appeal", "note", "r-prose", "The answer follows from the guide's rules or principles, but the guide does not say it."),
    "partial": ("Partly answers", "warning", "r-partial", "The guide answers part of the question."),
    "gap": ("Gap", "warning", "r-missing", "The guide does not address the question."),
    "differs": ("Differs", "note", "r-conflict", "The guide answers it differently from a past answer: a deliberate change, or a past answer to correct."),
    "out-of-scope": ("Out of scope", None, "r-out-of-scope", "Local policy, transport, testing tools, or one product: not for this guide."),
}
RESULT_ORDER = ["gap", "partial", "differs", "appeal", "answers", "out-of-scope"]
STATUS_LABEL = {"answered": "Answered", "partial": "Partly answered", "none": "No answer recorded"}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def ta_dir(repo: Path) -> Path | None:
    path = repo / "quality" / "ta"
    return path if (path / "index.yml").exists() else None


def _check_ref(where: str, ref: str, by_id: dict) -> None:
    card_id, loc = _ref_card(ref)
    c = by_id.get(card_id)
    if c is None:
        raise SystemExit(f"{where} names unknown card {card_id}")
    if loc and "--s" in loc and loc not in {s["id"] for s in c.statements}:
        raise SystemExit(f"{where} names unknown statement {loc}")
    if loc and "--s" not in loc and loc not in {f["id"] for f in c.meta.get("figures", [])}:
        raise SystemExit(f"{where} names unknown figure {ref}")


def load(repo: Path, by_id: dict) -> dict | None:
    base = ta_dir(repo)
    if base is None:
        return None
    index = read_yaml(base / "index.yml", {}) or {}
    pages = []
    for entry in index.get("pages", []):
        page = read_yaml(base / "pages" / f"{entry['id']}.yml", {}) or {}
        assess = read_yaml(base / "assess" / f"{entry['id']}.yml", {}) or {}
        found = {q["id"]: q for q in page.get("questions", [])}
        for qid, a in (assess.get("items") or {}).items():
            where = f"assess/{entry['id']}.yml: {qid}"
            if qid not in found:
                raise SystemExit(f"{where} is not a question on this page")
            if a.get("result") not in RESULTS:
                raise SystemExit(f"{where} has unknown result {a.get('result')}")
            for ref in a.get("guide") or []:
                _check_ref(where, ref, by_id)
            found[qid]["assess"] = a
        page["assessment"] = {k: v for k, v in assess.items() if k != "items"}
        pages.append(page)
    return {"dir": base, "excluded": index.get("excluded", {}), "pages": pages}


def severity(a: dict | None) -> str | None:
    if not a:
        return None
    return a.get("severity") or RESULTS[a["result"]][1]


def findings(data: dict | None) -> list[dict]:
    out = []
    for p in (data or {}).get("pages", []):
        for q in p["questions"]:
            a = q.get("assess")
            sev = severity(a)
            if not sev or not a.get("guide"):
                continue
            card, loc = _ref_card(a["guide"][0])
            note = " ".join((a.get("note") or "").split())
            ev = {"collection": KEY, "kind": a["result"], "tab_title": p["title"], "tab_id": p["id"], "item": q["id"],
                  "tab": " ".join(q["question"].split())}
            if a.get("recommendation"):
                ev["recommendation"] = " ".join(a["recommendation"].split())
            out.append({
                "id": f"qf-{q['id']}", "rule": RULE, "category": KEY, "severity": sev,
                "card": card, "location": loc if loc and "--s" in loc else None,
                "message": f"TA question ({p['title']}, {q['group']}): {RESULTS[a['result']][0]}. {note}".strip(),
                "evidence": ev,
            })
    return out


def evidence_with_link(ev: dict, root: str) -> str:
    tags = f'<div class="ev-tags"><span>{esc(RESULTS[ev["kind"]][0])}</span></div>'
    parts = [tags, f'<div class="ev"><span class="ev-k">Asked</span> {esc(ev["tab"])}</div>']
    if ev.get("recommendation"):
        parts.append(f'<div class="ev"><span class="ev-k">Recommendation</span> {esc(ev["recommendation"])}</div>')
    link = f'{root}{OUT_DIR}/{esc(ev["tab_id"])}/index.html#{esc(ev["item"])}'
    return f'<div class="evidence">{"".join(parts)}</div><p class="mini"><a href="{link}">See the TA question</a></p>'


# ---------------------------------------------------------------- pages

BANNER = ("Working analysis for the authors, from questions asked of AIRA's technical assistance service. "
          "Not part of the guide.")


def _badge(result: str) -> str:
    label, _, css, help_ = RESULTS[result]
    return f'<span class="tab-result {css}" title="{esc(help_)}">{esc(label)}</span>'


def _counts(page: dict) -> Counter:
    return Counter((q.get("assess") or {}).get("result", "unassessed") for q in page["questions"])


def _sev_counts(page: dict) -> list[int]:
    f = [0, 0, 0]
    for q in page["questions"]:
        a = q.get("assess")
        sev = severity(a)
        if sev and a.get("guide"):
            f[("issue", "warning", "note").index(sev)] += 1
    return f


def _result_line(cnt: Counter, total: int) -> str:
    parts = [f"{esc(RESULTS[r][0])} {cnt[r]}" for r in RESULT_ORDER if cnt[r]]
    if cnt["unassessed"]:
        parts.append(f"Not yet assessed {cnt['unassessed']}" if cnt["unassessed"] < total else "Not yet assessed")
    return " · ".join(parts)


def _years(q: dict) -> str:
    years = sorted({str(y) for y in q.get("years", [])})
    return years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}" if years else ""


def _field_links(q: dict, root: str, out: Path) -> str:
    links = []
    for f in q.get("fields", []):
        seg, n = f.split("-")
        if (out / "structure" / "segments" / seg.lower() / "index.html").exists():
            links.append(f'<a href="{root}structure/segments/{seg.lower()}/index.html#f{n}">{esc(f)}</a>')
        else:
            links.append(esc(f))
    return ", ".join(links)


def _question(q: dict, by_id: dict, root: str, out: Path) -> str:
    meta = [f"Asked {q.get('asked', 1)}×", _years(q), q.get("messages", ""), STATUS_LABEL.get(q.get("status"), "")]
    fields = _field_links(q, root, out)
    if fields:
        meta.append("Fields: " + fields)
    if q.get("related"):
        meta.append("Related: " + esc(", ".join(q["related"])))
    meta_html = " · ".join(m if m.startswith(("Fields", "Related")) else esc(m) for m in meta if m)
    answer = (f'<div class="ta-answer"><p class="ta-k">Answer given</p>{minimd.render(q["answer"])}</div>' if q.get("answer")
              else '<p class="ta-answer mini">No answer recorded.</p>')
    flags = "".join(f'<p class="ta-flag"><strong>Flagged when consolidated:</strong> {esc(f)}</p>' for f in q.get("flags", []))
    a = q.get("assess")
    if a:
        sev = severity(a)
        chip = (f' <a class="sev-chip sev-{sev}" href="{root}quality/index.html#qf-{esc(q["id"])}">{esc(sev.capitalize())}</a>'
                if sev and a.get("guide") else "")
        guide = ", ".join(_guide_link(r, by_id, root) for r in a.get("guide") or [])
        body = _badge(a["result"]) + chip
        if a.get("note"):
            body += f'<p class="tab-note">{esc(" ".join(a["note"].split()))}</p>'
        if a.get("recommendation"):
            body += f'<p class="tab-rec"><strong>Recommendation:</strong> {esc(" ".join(a["recommendation"].split()))}</p>'
        if guide:
            body += f'<p class="mini">In the guide: {guide}</p>'
        result_cls = RESULTS[a["result"]][2]
    else:
        body, result_cls = '<span class="mini">Not yet assessed against the guide.</span>', "r-unassessed"
    return f"""<section class="ta-q {result_cls}" id="{esc(q['id'])}">
<h3>{esc(q['question'])}</h3>
<p class="mini">{meta_html}</p>
<div class="ta-grid"><div>{answer}{flags}</div>
<div class="ta-assess"><p class="ta-k">Can the guide answer it?</p>{body}</div></div>
</section>"""


def page_html(p: dict, by_id: dict, root: str, out: Path) -> str:
    groups: dict[str, list] = {}
    for q in p["questions"]:
        groups.setdefault(q["group"], []).append(q)
    toc = "".join(f'<li><a href="#g-{i}">{esc(g)}</a> <span class="mini">{len(qs)}</span></li>' for i, (g, qs) in enumerate(groups.items()))
    sections = "".join(f'<h2 id="g-{i}">{esc(g)}</h2>' + "".join(_question(q, by_id, root, out) for q in qs)
                       for i, (g, qs) in enumerate(groups.items()))
    cnt = _counts(p)
    a = p.get("assessment") or {}
    summary = f'<h2>How well the guide answers these</h2><p>{esc(" ".join(a["summary"].split()))}</p>' if a.get("summary") else ""
    reviewed = (f'<p class="mini">Assessed {esc(a.get("reviewed", ""))} against the {esc(a.get("against", ""))}.</p>'
                if a.get("reviewed") else "")
    suggested = "".join(f"<li>{esc(s)}</li>" for s in p.get("suggested", []))
    suggested_html = (f'<details><summary>IG clarifications suggested when the TA records were consolidated ({len(p["suggested"])})</summary>'
                      f'<ul>{suggested}</ul></details>' if suggested else "")
    overview = minimd.render(p["overview"]) if p.get("overview") else ""
    return f"""<article class="page tabs ta">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}{OUT_DIR}/index.html">{TITLE}</a></nav>
<p class="eyebrow">TA questions · {"segment" if p["kind"] == "segment" else "topic"}</p>
<h1>{esc(p['title'])}</h1>
<p class="callout">{BANNER}</p>
<p class="stats">{len(p['questions'])} questions. Findings: {_sev_line(_sev_counts(p))}<br><span class="mini">{_result_line(cnt, len(p['questions']))}</span></p>
{summary}{reviewed}
<h2>What was asked</h2>
<div class="ta-overview">{overview}</div>
{suggested_html}
<ul class="ta-toc">{toc}</ul>
{sections}
</article>"""


def _sev_line(f: list[int]) -> str:
    parts = [f'<span class="sev-chip sev-{s}">{n} {s}{"s" if n != 1 else ""}</span>'
             for s, n in zip(("issue", "warning", "note"), f) if n]
    return " ".join(parts) or '<span class="mini">none</span>'


def index_html(data: dict, root: str) -> str:
    total = Counter()
    rows = {"segment": [], "topic": []}
    for p in data["pages"]:
        cnt = _counts(p)
        total.update(cnt)
        rows[p["kind"]].append(
            f'<tr><td><a href="{root}{OUT_DIR}/{esc(p["id"])}/index.html">{esc(p["title"])}</a></td><td class="n">{len(p["questions"])}</td>'
            f'<td>{_sev_line(_sev_counts(p))}<p class="mini">{_result_line(cnt, len(p["questions"]))}</p></td></tr>')
    n = sum(len(p["questions"]) for p in data["pages"])
    assessed = n - total["unassessed"]
    score = ""
    if assessed:
        score = "<ul class=\"tab-legend\">" + "".join(
            f"<li>{_badge(r)} {total[r]} ({round(100 * total[r] / assessed)}%)</li>" for r in RESULT_ORDER if total[r]) + "</ul>"
    legend = "".join(f"<li>{_badge(r)} {esc(RESULTS[r][3])}</li>" for r in RESULT_ORDER)
    ex = data.get("excluded") or {}
    table = lambda kind: (f'<table class="rules"><thead><tr><th>Page</th><th>Questions</th><th>Result</th></tr></thead>'
                          f'<tbody>{"".join(rows[kind])}</tbody></table>')
    return f"""<article class="page tabs ta">
<p class="eyebrow">Review</p>
<h1>{TITLE}</h1>
<p class="callout">{BANNER}</p>
<p class="lede">Implementers have asked AIRA's technical assistance service about HL7 v2 immunization messaging for ten
years. The guide should be able to answer those questions, directly or by appeal to its rules and principles. These pages
go through each question and record whether the current guide answers it, next to the answer given at the time. The past
answers are not reviewed here: they are there to copy into the guide, or to show where the guide now says something
different. Who asked is left out: it does not matter to the guide.</p>
<p>{n} questions, consolidated from the TA records, grouped by segment and field and then by topic. {assessed} assessed so far.
Left out: {ex.get("smm", 0)} questions about the Simple Message Mover (SMM), which is not in this guide's scope, and
{ex.get("not_generalizable", 0)} one-off troubleshooting questions that do not generalize. Questions the guide does not fully
answer also appear as quality findings (category "ta") on the section where the answer belongs.</p>
{"<h2>Coverage so far</h2>" + score if score else ""}
<h2>By segment</h2>{table("segment")}
<h2>By topic</h2>{table("topic")}
<h2>What the results mean</h2>
<ul class="tab-legend">{legend}</ul>
<p class="mini">Data: <code>quality/ta/</code> (pages published by <code>tools/import_ta.py</code> from the TA consolidation,
without who asked; assessments in <code>quality/ta/assess/</code>).</p>
</article>"""


def build_pages(out: Path, data: dict, by_id: dict, write) -> tuple[list[dict], dict]:
    """write(path, title, body, root). Returns the nav children and anchors."""
    write(out / OUT_DIR / "index.html", TITLE, index_html(data, "../"), "../")
    nav, anchors = [], {OUT_DIR: f"{OUT_DIR}/index.html"}
    for p in data["pages"]:
        anchor = f"{KEY}-{p['id']}"
        path = f"{OUT_DIR}/{p['id']}/index.html"
        write(out / path, f"TA questions: {p['title']}", page_html(p, by_id, "../../", out), "../../")
        nav.append({"i": anchor, "t": p["title"], "n": "", "p": path, "f": _sev_counts(p)})
        anchors[anchor] = path
    return nav, anchors


def card_panel(card_id: str, data: dict | None, root: str) -> str:
    if not data:
        return ""
    items = []
    for p in data["pages"]:
        for q in p["questions"]:
            a = q.get("assess") or {}
            if any(_ref_card(r)[0] == card_id for r in a.get("guide") or []):
                items.append(f'<li><a href="{root}{OUT_DIR}/{esc(p["id"])}/index.html#{esc(q["id"])}">{esc(q["question"])}</a> '
                             f'{_badge(a["result"])}</li>')
    if not items:
        return ""
    return (f'<section class="related tab-related"><h2>TA questions</h2><p class="mini">{BANNER}</p>'
            f'<ul>{"".join(items)}</ul></section>')
