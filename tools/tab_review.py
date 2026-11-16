"""Technical Advisory Bulletins (TABs): the list in data/tabs.yml and the comparisons in quality/tabs/<id>.yml.

- load():        reads both and checks that every guide reference (card, statement, figure) exists
- findings():    turns comparison results that need attention into quality findings (category "tab")
- build_pages(): writes the "TAB Comparison" pages (tabs/index.html and tabs/<id>/index.html)
- card_panel():  the "Technical Advisory Bulletins" panel on the sections a TAB affects
"""

from __future__ import annotations

import html
import shutil
from collections import Counter
from pathlib import Path

from guidecards import read_yaml

CATEGORY = {"tab": "TAB comparison"}
RULE_HELP = {"tab-review": "Reviewed comparison of a Technical Advisory Bulletin (TAB) with the guide."}

RESULTS = {  # result: (label, default severity, short help)
    "covered": ("Covered", None, "The guide says the same thing."),
    "prose": ("In narrative only", "note", "The guide says it, but in narrative rather than as a numbered conformance statement."),
    "reworded": ("Reworded", "note", "The guide says it differently; check that the meaning is unchanged."),
    "partial": ("Partly covered", "warning", "Some of it is in the guide."),
    "missing": ("Missing", "warning", "Not in the guide."),
    "conflict": ("Conflict", "issue", "The guide or the profiles say something different."),
    "guide-adds": ("Guide adds", "note", "A requirement in the guide that the TAB does not have."),
    "out-of-scope": ("Out of scope", None, "Outside the scope of this guide."),
}
RESULT_ORDER = ["conflict", "missing", "partial", "reworded", "prose", "covered", "guide-adds", "out-of-scope"]
OWNER_LABEL = {"narrative": "Narrative", "igamt": "IGAMT", "both": "Narrative and IGAMT", "decision": "CDC decision"}
KIND_LABEL = {"tab": "TAB", "overview": "About TABs", "summary": "Index of TABs"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def month(date) -> str:
    if not date:
        return ""
    y, m = str(date).split("-")[:2]
    return f"{MONTHS[int(m) - 1]} {y}"


def _ref_card(ref: str) -> tuple[str, str | None]:
    """Card ID and location (statement or figure ID) of a guide reference."""
    if "#" in ref:
        card, fig = ref.split("#", 1)
        return card, fig
    if "--s" in ref:
        return ref.split("--s", 1)[0], ref
    return ref, None


def load(repo: Path, by_id: dict) -> dict:
    """The TAB list and comparisons. Raises SystemExit on a reference to a card, statement, or figure that does not exist."""
    data = read_yaml(repo / "data" / "tabs.yml", {}) or {}
    tabs = data.get("tabs", [])
    seen = set()
    for t in tabs:
        if t["id"] in seen:
            raise SystemExit(f"tabs.yml: duplicate TAB id {t['id']}")
        seen.add(t["id"])
        t.setdefault("kind", "tab")
        for cid in t.get("cards", []):
            if cid not in by_id:
                raise SystemExit(f"tabs.yml: {t['id']} names unknown card {cid}")
        path = repo / "quality" / "tabs" / f"{t['id']}.yml"
        t["review"] = read_yaml(path, None) if path.exists() else None
        if t["review"]:
            item_ids = set()
            for it in t["review"].get("items", []):
                if it["id"] in item_ids:
                    raise SystemExit(f"{path.name}: duplicate item id {it['id']}")
                item_ids.add(it["id"])
                if it.get("result") not in RESULTS:
                    raise SystemExit(f"{path.name}: {it['id']} has unknown result {it.get('result')}")
                for ref in it.get("guide", []) or []:
                    card_id, loc = _ref_card(ref)
                    c = by_id.get(card_id)
                    if c is None:
                        raise SystemExit(f"{path.name}: {it['id']} names unknown card {card_id}")
                    if loc and "--s" in loc and loc not in {s["id"] for s in c.statements}:
                        raise SystemExit(f"{path.name}: {it['id']} names unknown statement {loc}")
                    if loc and "--s" not in loc and loc not in {f["id"] for f in c.meta.get("figures", [])}:
                        raise SystemExit(f"{path.name}: {it['id']} names unknown figure {ref}")
    for f in repo.glob("quality/tabs/*.yml"):
        if f.stem not in seen:
            raise SystemExit(f"quality/tabs/{f.name} has no entry in data/tabs.yml")
    if data.get("list_on") and data["list_on"] not in by_id:
        raise SystemExit(f"tabs.yml: list_on names unknown card {data['list_on']}")
    return {"page": data.get("page"), "list_on": data.get("list_on"), "tabs": tabs}


def severity(item: dict) -> str | None:
    return item.get("severity") or RESULTS[item["result"]][1]


def findings(data: dict) -> list[dict]:
    """Comparison items that need attention, as quality findings attached to the first guide section they name."""
    out = []
    for t in data["tabs"]:
        for it in (t.get("review") or {}).get("items", []):
            sev = severity(it)
            if not sev or not it.get("guide"):
                continue
            card, loc = _ref_card(it["guide"][0])
            label = RESULTS[it["result"]][0]
            note = " ".join((it.get("note") or "").split())
            ev = {"kind": it["result"], "tab_title": t["title"], "tab_id": t["id"], "item": it["id"]}
            if it.get("tab"):
                ev["tab"] = " ".join(it["tab"].split())
            if it.get("recommendation"):
                ev["recommendation"] = " ".join(it["recommendation"].split())
            if it.get("owner"):
                ev["owner"] = it["owner"]
            out.append({
                "id": f"qf-{it['id']}", "rule": "tab-review", "category": "tab", "severity": sev,
                "card": card, "location": loc if loc and "--s" in loc else None,
                "message": f"TAB {t['title']} ({it.get('section', '')}): {label}. {note}".strip(),
                "evidence": ev,
            })
    return out


def evidence_html(ev: dict) -> str:
    parts = []
    tags = [RESULTS.get(ev.get("kind"), (ev.get("kind"),))[0]]
    if ev.get("owner"):
        tags.append("Action: " + OWNER_LABEL.get(ev["owner"], ev["owner"]))
    parts.append('<div class="ev-tags">' + "".join(f"<span>{esc(x)}</span>" for x in tags if x) + "</div>")
    if ev.get("tab"):
        parts.append(f'<div class="ev"><span class="ev-k">TAB</span> {esc(ev["tab"])}</div>')
    if ev.get("recommendation"):
        parts.append(f'<div class="ev"><span class="ev-k">Recommendation</span> {esc(ev["recommendation"])}</div>')
    return f'<div class="evidence">{"".join(parts)}</div>'


# ---------------------------------------------------------------- pages

def _guide_link(ref: str, by_id: dict, root: str) -> str:
    card_id, loc = _ref_card(ref)
    c = by_id[card_id]
    if loc and "--s" in loc:
        n = loc.rsplit("--s", 1)[-1]
        return f'<a href="{root}{c.id}/index.html#{esc(loc)}">{esc(c.number)} s{esc(n)}</a>'
    if loc:
        fig = next(f for f in c.meta.get("figures", []) if f["id"] == loc)
        return f'<a href="{root}{c.id}/index.html#{esc(loc)}">Figure {esc(fig.get("number", ""))}</a>'
    return f'<a href="{root}{c.id}/index.html">{esc(c.number)} {esc(c.title)}</a>'


def _counts(review: dict | None) -> Counter:
    return Counter(it["result"] for it in (review or {}).get("items", []))


def _sev_counts(review: dict | None) -> list[int]:
    """Issues, warnings, and notes: the same counts as the findings (and the contents menu)."""
    f = [0, 0, 0]
    for it in (review or {}).get("items", []):
        sev = severity(it)
        if sev and it.get("guide"):
            f[("issue", "warning", "note").index(sev)] += 1
    return f


def _sev_summary(review: dict | None) -> str:
    parts = [f'<span class="sev-chip sev-{s}">{n} {s}{"s" if n != 1 else ""}</span>'
             for s, n in zip(("issue", "warning", "note"), _sev_counts(review)) if n]
    return " ".join(parts) or '<span class="mini">No findings</span>'


def _badge(result: str) -> str:
    return f'<span class="tab-result r-{esc(result)}" title="{esc(RESULTS[result][2])}">{esc(RESULTS[result][0])}</span>'


def _tab_links(t: dict, root: str) -> str:
    local = f"{root}tabs/files/{Path(t['file']).name}"
    return (f'<a href="{esc(t["url"])}" rel="noopener" target="_blank">Published PDF</a> · '
            f'<a href="{esc(local)}">Copy in this repository</a>')


def index_page(data: dict, by_id: dict, root: str) -> str:
    rows = []
    for t in data["tabs"]:
        cnt = _counts(t.get("review"))
        if t["kind"] == "summary":
            status = '<span class="mini">Not compared (an index of TABs, not kept current)</span>'
        elif t.get("review"):
            status = (f'<p>{_sev_summary(t["review"])}</p><p class="mini">'
                      + " · ".join(f'{esc(RESULTS[r][0])} {cnt[r]}' for r in RESULT_ORDER if cnt[r]) + "</p>")
        else:
            status = '<span class="mini">Not yet compared</span>'
        title = (f'<a href="{root}tabs/{esc(t["id"])}/index.html">{esc(t["title"])}</a>' if t["kind"] != "summary"
                 else esc(t["title"]))
        rows.append(f'<tr><td>{title}<p class="mini">{esc(KIND_LABEL[t["kind"]])}</p></td><td class="nowrap">{esc(month(t.get("date")))}</td>'
                    f'<td>{status}</td><td class="nowrap">{_tab_links(t, root)}</td></tr>')
    legend = "".join(f"<li>{_badge(r)} {esc(RESULTS[r][2])}</li>" for r in RESULT_ORDER)
    n_done = sum(1 for t in data["tabs"] if t.get("review"))
    n_tabs = sum(1 for t in data["tabs"] if t["kind"] != "summary")
    return f"""<article class="page tabs">
<p class="eyebrow">Review</p>
<h1>TAB Comparison</h1>
<p class="lede">Technical Advisory Bulletins (TABs) are published community specifications for the v2.5.1 Implementation
Guide for Immunization Messaging, developed by AIRA and CDC and approved by AIRA's Standards and Interoperability Steering
Committee (SISC). This guide is meant to fold them in. These pages check, requirement by requirement, that it does: nothing
missed, and nothing that contradicts a TAB.</p>
<p>Each TAB links to its published PDF on the <a href="{esc(data.get('page') or '')}" rel="noopener" target="_blank">AIRA
repository</a> and to the copy kept with this guide's source. {n_done} of {n_tabs} TABs have been compared so far. Results that need
attention also appear as quality findings on the guide sections they concern.</p>
<table class="rules tab-index"><thead><tr><th>TAB</th><th>Published</th><th>Comparison</th><th>Document</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>What the results mean</h2>
<ul class="tab-legend">{legend}</ul>
</article>"""


def tab_page(t: dict, by_id: dict, root: str) -> str:
    review = t.get("review")
    cards = "".join(f"<li>{_guide_link(cid, by_id, root)}</li>" for cid in t.get("cards", []))
    cards_html = f'<h2>Guide sections it affects</h2><ul class="tab-cards">{cards}</ul>' if cards else ""
    if not review:
        body = '<p class="callout">This TAB has not been compared with the guide yet.</p>'
    else:
        cnt = _counts(review)
        counts = (f'Findings: {_sev_summary(review)}<br><span class="mini">Results: '
                  + " · ".join(f'{esc(RESULTS[r][0])} {cnt[r]}' for r in RESULT_ORDER if cnt[r]) + "</span>")
        rows = []
        for it in review.get("items", []):
            guide = ", ".join(_guide_link(r, by_id, root) for r in it.get("guide", []) or []) or "—"
            sev = severity(it) if it["result"] != "covered" or it.get("severity") else None
            finding = (f' <a class="sev-chip sev-{sev}" href="{root}quality/index.html#qf-{esc(it["id"])}" '
                       f'title="Quality finding qf-{esc(it["id"])}">{esc(sev.capitalize())}</a>'
                       if sev and it.get("guide") else "")
            extra = ""
            if it.get("note"):
                extra += f'<p class="tab-note">{esc(" ".join(it["note"].split()))}</p>'
            if it.get("recommendation"):
                extra += f'<p class="tab-rec"><strong>Recommendation:</strong> {esc(" ".join(it["recommendation"].split()))}</p>'
            if it.get("owner") and it["result"] != "covered":
                extra += f'<p class="mini">Action: {esc(OWNER_LABEL.get(it["owner"], it["owner"]))}</p>'
            tab_text = esc(" ".join((it.get("tab") or "").split())) or '<span class="mini">(the guide only)</span>'
            verb = f'<span class="tab-verb">{esc(it["verb"])}</span> ' if it.get("verb") else ""
            where = esc(it.get("section", "")) + (f' <span class="mini">p. {esc(it["page"])}</span>' if it.get("page") else "")
            rows.append(f'<tr id="{esc(it["id"])}" class="r-{esc(it["result"])}"><td><p class="tab-where">{where}</p>{verb}{tab_text}</td>'
                        f'<td>{_badge(it["result"])}{finding}{extra}</td><td>{guide}</td></tr>')
        summary = f'<p>{esc(" ".join(review.get("summary", "").split()))}</p>' if review.get("summary") else ""
        body = f"""<h2>Summary</h2>{summary}
<p class="stats">{counts}</p>
<p class="mini">Reviewed {esc(review.get('reviewed', ''))} against the {esc(review.get('against', ''))}.
Recorded in <code>quality/tabs/{esc(t['id'])}.yml</code>.</p>
<h2>Requirement by requirement</h2>
<table class="tab-items"><thead><tr><th>The TAB says</th><th>Result</th><th>In the guide</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>"""
    return f"""<article class="page tabs">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}tabs/index.html">TAB Comparison</a></nav>
<p class="eyebrow">Technical Advisory Bulletin · {esc(month(t.get('date')))}</p>
<h1>{esc(t['title'])}</h1>
<p class="lede">{esc(' '.join(t.get('summary', '').split()))}</p>
<p>{_tab_links(t, root)}</p>
{cards_html}
{body}
</article>"""


def build_pages(out: Path, repo: Path, data: dict, by_id: dict, write) -> tuple[list[dict], dict]:
    """Writes the pages; returns the nav children and anchors. write(path, title, body, anchor, root)."""
    files = out / "tabs" / "files"
    files.mkdir(parents=True, exist_ok=True)
    for t in data["tabs"]:
        src = repo / t["file"]
        if not src.exists():
            raise SystemExit(f"tabs.yml: {t['id']} file {t['file']} not found")
        shutil.copy2(src, files / src.name)
    write(out / "tabs" / "index.html", "TAB Comparison", index_page(data, by_id, "../"), "tabs", "../")
    nav, anchors = [], {"tabs": "tabs/index.html"}
    for t in data["tabs"]:
        if t["kind"] == "summary":
            continue
        anchor = f"tab-{t['id']}"
        write(out / "tabs" / t["id"] / "index.html", t["title"], tab_page(t, by_id, "../../"), anchor, "../../")
        f = [0, 0, 0]
        for it in (t.get("review") or {}).get("items", []):
            sev = severity(it)
            if sev and it.get("guide"):
                f[("issue", "warning", "note").index(sev)] += 1
        nav.append({"i": anchor, "t": _short(t), "n": "", "p": f"tabs/{t['id']}/index.html", "f": f})
        anchors[anchor] = f"tabs/{t['id']}/index.html"
    return nav, anchors


def _short(t: dict) -> str:
    title = t["title"].split(":")[0] if t["id"] != "phone-and-email" else "Messaging Phone and Email"
    return title


def card_panel(card_id: str, data: dict | None, root: str) -> str:
    """Links to the TABs that affect this section."""
    if not data:
        return ""
    if card_id == data.get("list_on"):
        tabs = [t for t in data["tabs"] if t["kind"] == "tab"] + [t for t in data["tabs"] if t["kind"] != "tab"]
    else:
        tabs = [t for t in data["tabs"] if card_id in t.get("cards", [])]
    if not tabs:
        return ""
    def li(t):
        meta = [month(t.get("date"))] if t.get("date") else []
        meta = " · ".join(esc(m) for m in meta)
        if t["kind"] != "summary":
            label = "comparison with this guide" if t.get("review") else "not yet compared with this guide"
            meta += (" · " if meta else "") + f'<a href="{root}tabs/{esc(t["id"])}/index.html">{label}</a>'
        return (f'<li><a href="{esc(t["url"])}" rel="noopener" target="_blank">{esc(t["title"])}</a> '
                f'<span class="mini">{meta}</span></li>')
    return (f'<section class="related tab-related"><h2>Technical Advisory Bulletins</h2><ul>{"".join(li(t) for t in tabs)}</ul>'
            f'<p class="mini">All TABs are on the <a href="{esc(data.get("page") or "")}" rel="noopener" target="_blank">AIRA repository</a>. '
            f'<a href="{root}tabs/index.html">TAB Comparison</a> checks how this guide folds them in.</p></section>'
            if card_id == data.get("list_on") else
            f'<section class="related tab-related"><h2>Technical Advisory Bulletins</h2><ul>{"".join(li(t) for t in tabs)}</ul></section>')
