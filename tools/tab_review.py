"""Reviewed comparisons of published community guidance with the guide, requirement by requirement.

Two collections share this code (see COLLECTIONS):

- TABs:  Technical Advisory Bulletins, listed in data/tabs.yml, compared in quality/tabs/<id>.yml, pages under tabs/
- SISC:  SISC guidance documents published before the TABs, listed in data/sisc-guidance.yml, compared in
         quality/sisc/<id>.yml, pages under sisc/

- load():        reads a list and its comparisons, and checks that every guide reference (card, statement, figure) exists
- findings():    turns comparison results that need attention into quality findings
- build_pages(): writes the comparison pages (<dir>/index.html and <dir>/<id>/index.html)
- card_panel():  the panel on the sections a document affects
"""

from __future__ import annotations

import html
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from guidecards import read_yaml


@dataclass(frozen=True)
class Collection:
    key: str            # finding category, and the prefix of nav anchors
    data_file: str      # the list of documents
    list_key: str       # the key in data_file that holds the list
    review_dir: str     # one comparison file per document
    out_dir: str        # site folder (also where the source documents are kept in the repository)
    title: str          # page and menu title
    noun: str           # a document, in finding messages
    short: str          # a document, in the evidence label and table heading
    panel: str          # heading of the panel on affected sections
    eyebrow: str        # above a document's title
    text_field: str     # item field holding what the document says
    rule: str
    rule_help: str
    intro: str          # HTML; {page} is replaced by the source page URL


TAB = Collection(
    key="tab", data_file="data/tabs.yml", list_key="tabs", review_dir="quality/tabs", out_dir="tabs",
    title="TAB Comparison", noun="TAB", short="TAB", panel="Technical Advisory Bulletins",
    eyebrow="Technical Advisory Bulletin", text_field="tab", rule="tab-review",
    rule_help="Reviewed comparison of a Technical Advisory Bulletin (TAB) with the guide.",
    intro="""<p class="lede">Technical Advisory Bulletins (TABs) are published community specifications for the v2.5.1 Implementation
Guide for Immunization Messaging, developed by AIRA and CDC and approved by AIRA's Standards and Interoperability Steering
Committee (SISC). This guide is meant to fold them in. These pages check, requirement by requirement, that it does: nothing
missed, and nothing that contradicts a TAB.</p>""",
)

SISC = Collection(
    key="sisc", data_file="data/sisc-guidance.yml", list_key="documents", review_dir="quality/sisc", out_dir="sisc",
    title="SISC Guidance", noun="SISC guidance", short="Guidance", panel="SISC Guidance Documents",
    eyebrow="SISC guidance", text_field="doc", rule="sisc-review",
    rule_help="Reviewed comparison of a SISC guidance document (published before the TABs) with the guide.",
    intro="""<p class="lede">Before the TAB series began in 2024, AIRA's Standards and Interoperability Steering Committee (SISC)
published guidance documents, with CDC, that clarified how to implement Release 1.5. Implementers built to them, and some TABs
build on them. These pages check, requirement by requirement, whether this guide folds each one in, so that nothing
implementers rely on is dropped by accident.</p>
<p>Two related documents are compared elsewhere. The 2023 draft guidance on a national set of error codes became part of the
<a href="{root}tabs/ack-messaging/index.html">ACK TAB</a>; the 2017 version listed here is compared only for what the TAB did not
carry over. The 2015 MIROW micro-guide on validating lot numbers was replaced by the unit of sale and unit of use lot number
guidance listed here. A few related documents published by AIRA or the Immunization Integration Program, rather than SISC,
are listed here too; each one's page says so.</p>""",
)

COLLECTIONS = {c.key: c for c in (TAB, SISC)}
CATEGORY = {"tab": "TAB comparison", "sisc": "SISC guidance comparison"}
RULE_HELP = {c.rule: c.rule_help for c in COLLECTIONS.values()}

RESULTS = {  # result: (label, default severity, short help)
    "covered": ("Covered", None, "The guide says the same thing."),
    "prose": ("In narrative only", "note", "The guide says it, but in narrative rather than as a numbered conformance statement."),
    "reworded": ("Reworded", "note", "The guide says it differently; check that the meaning is unchanged."),
    "partial": ("Partly covered", "warning", "Some of it is in the guide."),
    "missing": ("Missing", "warning", "Not in the guide."),
    "conflict": ("Conflict", "issue", "The guide or the profiles say something different."),
    "guide-adds": ("Guide adds", "note", "A requirement in the guide that the document does not have."),
    "out-of-scope": ("Out of scope", None, "Outside the scope of this guide."),
}
RESULT_ORDER = ["conflict", "missing", "partial", "reworded", "prose", "covered", "guide-adds", "out-of-scope"]
OWNER_LABEL = {"narrative": "Narrative", "igamt": "IGAMT", "both": "Narrative and IGAMT", "decision": "CDC decision"}
KIND_LABEL = {"tab": "TAB", "overview": "About TABs", "summary": "Index of TABs", "guidance": "SISC guidance", "faq": "SISC FAQ"}
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


def load(repo: Path, by_id: dict, coll: Collection = TAB) -> dict:
    """A document list and its comparisons. Raises SystemExit on a reference to a card, statement, or figure that does not exist."""
    data_name = Path(coll.data_file).name
    data = read_yaml(repo / coll.data_file, {}) or {}
    docs = data.get(coll.list_key, [])
    seen = set()
    for t in docs:
        if t["id"] in seen:
            raise SystemExit(f"{data_name}: duplicate id {t['id']}")
        seen.add(t["id"])
        t.setdefault("kind", "tab" if coll is TAB else "guidance")
        if t["kind"] not in KIND_LABEL:
            raise SystemExit(f"{data_name}: {t['id']} has unknown kind {t['kind']}")
        for cid in t.get("cards", []):
            if cid not in by_id:
                raise SystemExit(f"{data_name}: {t['id']} names unknown card {cid}")
        path = repo / coll.review_dir / f"{t['id']}.yml"
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
    for f in repo.glob(f"{coll.review_dir}/*.yml"):
        if f.stem not in seen:
            raise SystemExit(f"{coll.review_dir}/{f.name} has no entry in {coll.data_file}")
    if data.get("list_on") and data["list_on"] not in by_id:
        raise SystemExit(f"{data_name}: list_on names unknown card {data['list_on']}")
    return {"coll": coll, "page": data.get("page"), "list_on": data.get("list_on"), "docs": docs}


def load_all(repo: Path, by_id: dict) -> dict[str, dict]:
    """Every collection whose list exists, keyed by collection key."""
    return {k: load(repo, by_id, c) for k, c in COLLECTIONS.items() if (repo / c.data_file).exists()}


def severity(item: dict) -> str | None:
    return item.get("severity") or RESULTS[item["result"]][1]


def findings(data: dict) -> list[dict]:
    """Comparison items that need attention, as quality findings attached to the first guide section they name."""
    coll = data["coll"]
    out = []
    for t in data["docs"]:
        for it in (t.get("review") or {}).get("items", []):
            sev = severity(it)
            if not sev or not it.get("guide"):
                continue
            card, loc = _ref_card(it["guide"][0])
            label = RESULTS[it["result"]][0]
            note = " ".join((it.get("note") or "").split())
            ev = {"kind": it["result"], "tab_title": t["title"], "tab_id": t["id"], "item": it["id"], "collection": coll.key}
            if it.get(coll.text_field):
                ev["tab"] = " ".join(it[coll.text_field].split())
            if it.get("recommendation"):
                ev["recommendation"] = " ".join(it["recommendation"].split())
            if it.get("owner"):
                ev["owner"] = it["owner"]
            out.append({
                "id": f"qf-{it['id']}", "rule": coll.rule, "category": coll.key, "severity": sev,
                "card": card, "location": loc if loc and "--s" in loc else None,
                "message": f"{coll.noun} {t['title']} ({it.get('section', '')}): {label}. {note}".strip(),
                "evidence": ev,
            })
    return out


def evidence_html(ev: dict) -> str:
    coll = COLLECTIONS[ev.get("collection", "tab")]
    parts = []
    tags = [RESULTS.get(ev.get("kind"), (ev.get("kind"),))[0]]
    if ev.get("owner"):
        tags.append("Action: " + OWNER_LABEL.get(ev["owner"], ev["owner"]))
    parts.append('<div class="ev-tags">' + "".join(f"<span>{esc(x)}</span>" for x in tags if x) + "</div>")
    if ev.get("tab"):
        parts.append(f'<div class="ev"><span class="ev-k">{esc(coll.short)}</span> {esc(ev["tab"])}</div>')
    if ev.get("recommendation"):
        parts.append(f'<div class="ev"><span class="ev-k">Recommendation</span> {esc(ev["recommendation"])}</div>')
    return f'<div class="evidence">{"".join(parts)}</div>'


def evidence_with_link(ev: dict, root: str) -> str:
    """The evidence, and a link to the comparison it comes from."""
    coll = COLLECTIONS[ev.get("collection", "tab")]
    link = f"{root}{coll.out_dir}/{esc(ev['tab_id'])}/index.html#{esc(ev['item'])}"
    label = "See the TAB comparison" if coll is TAB else "See the SISC guidance comparison"
    return evidence_html(ev) + f'<p class="mini"><a href="{link}">{label}</a></p>'


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


def _doc_links(t: dict, root: str, coll: Collection) -> str:
    links = []
    if t.get("url"):
        label = "Published PDF" if str(t["url"]).lower().endswith(".pdf") else "Published document"
        links.append(f'<a href="{esc(t["url"])}" rel="noopener" target="_blank">{label}</a>')
    if t.get("file"):
        links.append(f'<a href="{esc(f"{root}{coll.out_dir}/files/{Path(t["file"]).name}")}">Copy in this repository</a>')
    return " · ".join(links) or '<span class="mini">Published copy not yet located</span>'


def index_page(data: dict, by_id: dict, root: str) -> str:
    coll = data["coll"]
    rows = []
    for t in data["docs"]:
        cnt = _counts(t.get("review"))
        if t["kind"] == "summary":
            status = '<span class="mini">Not compared (an index of TABs, not kept current)</span>'
        elif t.get("review"):
            status = (f'<p>{_sev_summary(t["review"])}</p><p class="mini">'
                      + " · ".join(f'{esc(RESULTS[r][0])} {cnt[r]}' for r in RESULT_ORDER if cnt[r]) + "</p>")
        else:
            status = '<span class="mini">Not yet compared</span>'
        title = (f'<a href="{root}{coll.out_dir}/{esc(t["id"])}/index.html">{esc(t["title"])}</a>' if t["kind"] != "summary"
                 else esc(t["title"]))
        rows.append(f'<tr><td>{title}<p class="mini">{esc(KIND_LABEL[t["kind"]])}</p></td><td class="nowrap">{esc(month(t.get("date")))}</td>'
                    f'<td>{status}</td><td class="nowrap">{_doc_links(t, root, coll)}</td></tr>')
    legend = "".join(f"<li>{_badge(r)} {esc(RESULTS[r][2])}</li>" for r in RESULT_ORDER)
    n_done = sum(1 for t in data["docs"] if t.get("review"))
    n_docs = sum(1 for t in data["docs"] if t["kind"] != "summary")
    noun_pl = "TABs" if coll is TAB else "documents"
    where = (f'<a href="{esc(data.get("page") or "")}" rel="noopener" target="_blank">AIRA repository</a>'
             if data.get("page") else "AIRA repository")
    return f"""<article class="page tabs">
<p class="eyebrow">Review</p>
<h1>{esc(coll.title)}</h1>
{coll.intro.replace("{root}", root)}
<p>Each {"TAB" if coll is TAB else "document"} links to its published {"PDF" if coll is TAB else "copy"} on the {where} and to the copy kept with this
guide's source. {n_done} of {n_docs} {noun_pl} have been compared so far. Results that need attention also appear as quality
findings on the guide sections they concern.</p>
<table class="rules tab-index"><thead><tr><th>{"TAB" if coll is TAB else "Document"}</th><th>Published</th><th>Comparison</th><th>Document</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>What the results mean</h2>
<ul class="tab-legend">{legend}</ul>
</article>"""


def doc_page(t: dict, by_id: dict, root: str, coll: Collection = TAB) -> str:
    review = t.get("review")
    cards = "".join(f"<li>{_guide_link(cid, by_id, root)}</li>" for cid in t.get("cards", []))
    cards_html = f'<h2>Guide sections it affects</h2><ul class="tab-cards">{cards}</ul>' if cards else ""
    noun = "TAB" if coll is TAB else "document"
    if not review:
        body = f'<p class="callout">This {noun} has not been compared with the guide yet.</p>'
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
            doc_text = esc(" ".join((it.get(coll.text_field) or "").split())) or '<span class="mini">(the guide only)</span>'
            verb = f'<span class="tab-verb">{esc(it["verb"])}</span> ' if it.get("verb") else ""
            where = esc(it.get("section", "")) + (f' <span class="mini">p. {esc(it["page"])}</span>' if it.get("page") else "")
            rows.append(f'<tr id="{esc(it["id"])}" class="r-{esc(it["result"])}"><td><p class="tab-where">{where}</p>{verb}{doc_text}</td>'
                        f'<td>{_badge(it["result"])}{finding}{extra}</td><td>{guide}</td></tr>')
        summary = f'<p>{esc(" ".join(review.get("summary", "").split()))}</p>' if review.get("summary") else ""
        body = f"""<h2>Summary</h2>{summary}
<p class="stats">{counts}</p>
<p class="mini">Reviewed {esc(review.get('reviewed', ''))} against the {esc(review.get('against', ''))}.
Recorded in <code>{esc(coll.review_dir)}/{esc(t['id'])}.yml</code>.</p>
<h2>Requirement by requirement</h2>
<table class="tab-items"><thead><tr><th>The {esc(coll.short if coll is TAB else "guidance")} says</th><th>Result</th><th>In the guide</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>"""
    eyebrow = esc(coll.eyebrow if t["kind"] != "faq" else "SISC FAQ")
    note = f'<p class="callout">{esc(" ".join(t["source_note"].split()))}</p>' if t.get("source_note") else ""
    return f"""<article class="page tabs">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}{coll.out_dir}/index.html">{esc(coll.title)}</a></nav>
<p class="eyebrow">{eyebrow} · {esc(month(t.get('date')))}</p>
<h1>{esc(t['title'])}</h1>
<p class="lede">{esc(' '.join(t.get('summary', '').split()))}</p>
<p>{_doc_links(t, root, coll)}</p>
{note}
{cards_html}
{body}
</article>"""


tab_page = doc_page  # earlier name


def build_pages(out: Path, repo: Path, data: dict, by_id: dict, write) -> tuple[list[dict], dict]:
    """Writes the pages; returns the nav children and anchors. write(path, title, body, anchor, root)."""
    coll = data["coll"]
    base = out / coll.out_dir
    files = base / "files"
    files.mkdir(parents=True, exist_ok=True)
    for t in data["docs"]:
        if not t.get("file"):
            continue
        src = repo / t["file"]
        if not src.exists():
            raise SystemExit(f"{coll.data_file}: {t['id']} file {t['file']} not found")
        shutil.copy2(src, files / src.name)
    index_anchor = "tabs" if coll is TAB else coll.out_dir
    write(base / "index.html", coll.title, index_page(data, by_id, "../"), index_anchor, "../")
    nav, anchors = [], {index_anchor: f"{coll.out_dir}/index.html"}
    for t in data["docs"]:
        if t["kind"] == "summary":
            continue
        anchor = f"{coll.key}-{t['id']}"
        write(base / t["id"] / "index.html", t["title"], doc_page(t, by_id, "../../", coll), anchor, "../../")
        nav.append({"i": anchor, "t": _short(t), "n": "", "p": f"{coll.out_dir}/{t['id']}/index.html", "f": _sev_counts(t.get("review"))})
        anchors[anchor] = f"{coll.out_dir}/{t['id']}/index.html"
    return nav, anchors


def _short(t: dict) -> str:
    if t.get("short"):
        return t["short"]
    return t["title"].split(":")[0] if t["id"] != "phone-and-email" else "Messaging Phone and Email"


def card_panel(card_id: str, data: dict | None, root: str) -> str:
    """Links to the documents that affect this section."""
    if not data:
        return ""
    coll = data["coll"]
    if card_id == data.get("list_on"):
        docs = [t for t in data["docs"] if t["kind"] == "tab"] + [t for t in data["docs"] if t["kind"] != "tab"]
    else:
        docs = [t for t in data["docs"] if card_id in t.get("cards", [])]
    if not docs:
        return ""

    def li(t):
        meta = [month(t.get("date"))] if t.get("date") else []
        meta = " · ".join(esc(m) for m in meta)
        if t["kind"] != "summary":
            label = "comparison with this guide" if t.get("review") else "not yet compared with this guide"
            meta += (" · " if meta else "") + f'<a href="{root}{coll.out_dir}/{esc(t["id"])}/index.html">{label}</a>'
        title = (f'<a href="{esc(t["url"])}" rel="noopener" target="_blank">{esc(t["title"])}</a>' if t.get("url")
                 else esc(t["title"]))
        return f'<li>{title} <span class="mini">{meta}</span></li>'

    items = "".join(li(t) for t in docs)
    if card_id == data.get("list_on"):
        return (f'<section class="related tab-related"><h2>{esc(coll.panel)}</h2><ul>{items}</ul>'
                f'<p class="mini">All TABs are on the <a href="{esc(data.get("page") or "")}" rel="noopener" target="_blank">AIRA repository</a>. '
                f'<a href="{root}{coll.out_dir}/index.html">{esc(coll.title)}</a> checks how this guide folds them in.</p></section>')
    return f'<section class="related tab-related"><h2>{esc(coll.panel)}</h2><ul>{items}</ul></section>'
