"""The "Proposed Analyses" page (quality/proposals/index.html), rendered from quality/proposed-analyses.yml.

Proposes further comparisons and checks for CDC to consider. Each proposal is a comment target.
"""

from __future__ import annotations

import html
from pathlib import Path

import minimd
from guidecards import examples_shown, read_yaml

SOURCE = Path("quality") / "proposed-analyses.yml"


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def load(repo: Path) -> dict | None:
    path = repo / SOURCE
    return read_yaml(path, {}) if path.exists() else None


def review_targets(data: dict) -> list[dict]:
    """Comment targets: the whole page, then each proposal."""
    out = [{"i": 0, "label": "Whole page"}]
    for n, p in enumerate(data.get("proposals", []), 1):
        out.append({"i": n, "label": p["title"][:110], "snippet": p["id"]})
    return out


def page(data: dict, root: str, by_id: dict) -> str:
    def card_link(cid: str) -> str:
        c = by_id.get(cid)
        if not c:
            return f"<code>{esc(cid)}</code>"
        return f'<a href="{root}{c.id}/index.html">{esc(c.number + " " + c.title)}</a>'

    def bullets(items) -> str:
        return "<ul>" + "".join(f"<li>{minimd.inline(i)}</li>" for i in items) + "</ul>" if items else ""

    def current_item(c: dict) -> str:
        title = esc(c["title"])
        if c.get("link"):
            title = f'<a href="{root}{esc(c["link"])}">{title}</a>'
        return f"<li><strong>{title}</strong>: {esc(c['text'])}</li>"

    current = "".join(current_item(c) for c in data.get("current", [])
                      if examples_shown() or not str(c.get("link", "")).startswith("examples/"))

    proposals = data.get("proposals", [])
    number = {p["id"]: n for n, p in enumerate(proposals, 1)}
    toc, sections = [], []
    for g in data.get("groups", []):
        items = [p for p in proposals if p.get("group") == g["id"]]
        if not items:
            continue
        toc.append(f'<li><a href="#group-{esc(g["id"])}">{esc(g["title"])}</a><ol>'
                   + "".join(f'<li value="{number[p["id"]]}"><a href="#{esc(p["id"])}">{esc(p["title"])}</a></li>' for p in items)
                   + "</ol></li>")
        parts = [f'<section id="group-{esc(g["id"])}"><h2>{esc(g["title"])}</h2><p>{esc(g.get("text", ""))}</p>']
        for p in items:
            cards = ""
            if p.get("cards"):
                cards = "<h4>Guide sections most likely affected</h4><ul>" + "".join(f"<li>{card_link(c)}</li>" for c in p["cards"]) + "</ul>"
            scope = f'<p class="callout"><strong>Scope:</strong> {minimd.inline(p["scope"])}</p>' if p.get("scope") else ""
            parts.append(
                f'<article class="proposal" id="{esc(p["id"])}"><h3><span class="num">{number[p["id"]]}</span> {esc(p["title"])}'
                f' <span class="f-id">{esc(p["id"])}</span></h3>'
                f'<h4>Why</h4>{minimd.render(p.get("why", ""))}'
                f'<h4>Approach</h4>{bullets(p.get("approach"))}'
                f'<h4>Compared with</h4>{bullets(p.get("sources"))}'
                f'<h4>What CDC would get</h4><p>{minimd.inline(p.get("output", ""))}</p>'
                f'{cards}{scope}</article>')
        parts.append("</section>")
        sections.append("".join(parts))

    return f"""<article class="page about proposals">
<p class="eyebrow">For discussion with CDC</p>
<h1>{esc(data.get("title", "Proposed Analyses"))}</h1>
<p class="lede">{esc(data.get("intro", ""))}</p>
<p class="callout">{esc(data.get("principle", ""))}</p>
<nav class="page-toc" aria-label="On this page"><ol>
<li><a href="#current">Checks already in place</a></li>
{''.join(toc)}
</ol></nav>
<section id="current"><h2>Checks already in place</h2><ul>{current}</ul></section>
{''.join(sections)}
<p>Questions, priorities, or other ideas are welcome as comments on this page.</p>
</article>"""
