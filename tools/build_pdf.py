#!/usr/bin/env python3
"""Build a PDF edition of the guide (prototype).

    python tools/build_pdf.py                  # writes output/pdf/guide.html and output/pdf/<name>.pdf
    python tools/build_pdf.py --chrome PATH    # a Chrome or Edge executable (found automatically on Windows)

The PDF has the reader content of the release edition of the website (no author material), reorganized for reading in
order and on paper:

- one continuous document with a cover, a table of contents with page numbers, and PDF bookmarks;
- each section's conformance statements kept with it, numbered as on the website (s1, s2, ...);
- example messages gathered in Appendix A, each shown as the clip it is about, with the base messages printed once;
  sections point to their examples by number and page;
- chapter 7 organized by message profile (segment tree, then its OBX co-constraints), then by segment in message order,
  with the variants (flavors) of a segment shown as their differences from the main flavor;
- value sets moved to Appendix E; large and externally maintained code systems (CVX, MVX, NDC, ...) are described
  but their codes are not printed.

Rendering: one HTML file is printed by headless Chrome; PyMuPDF then reads where each anchor landed, the page numbers are
filled in and the file printed again, and the running heads, page numbers, and bookmarks are added. Needs PyYAML and
PyMuPDF, and Chrome or Edge.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import view  # noqa: E402

view.set_edition("release")  # before the site modules render anything

import build_site  # noqa: E402
import check_cards  # noqa: E402
import hl7msg  # noqa: E402
import minimd  # noqa: E402
import site_err5  # noqa: E402
import site_examples  # noqa: E402
from guidecards import CARDS_DIR, DATA_DIR, META, REPO, norm_title, read_yaml, walk, write_text  # noqa: E402
from site_structure import Structure, slug  # noqa: E402
from structure_index import PROFILE_ORDER, Model  # noqa: E402

PDF_SRC = REPO / "site" / "pdf"
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "msedge",
]
# value sets whose codes are not printed: maintained outside the guide and changed often, or very long
LIST_LIMIT = 120
SEGMENT_ORDER = ["MSH", "SFT", "MSA", "ERR", "QAK", "QPD", "RCP", "PID", "PD1", "NK1", "PV1", "PV2", "GT1", "IN1", "IN2", "IN3",
                 "ORC", "TQ1", "TQ2", "RXA", "RXR", "OBX", "NTE", "DSC"]

esc = build_site.esc


# =========================================================================== links

def pdf_links(fragment: str, web: str) -> str:
    """Turn the website's relative links (built with root "") into links within the PDF."""
    def repl(m):
        href = m.group(1)
        if re.match(r"^(https?:|mailto:|#)", href):
            return m.group(0)
        path, _, frag = href.partition("#")
        path = path.removesuffix("index.html").strip("/")
        parts = path.split("/") if path else []
        target = None
        if parts[:1] == ["structure"]:
            if len(parts) == 1:
                target = "ch7"
            elif parts[1] == "segments" and len(parts) == 3:
                target = f"seg-{parts[2]}" + (f"-{frag}" if frag else "")
            elif parts[1] == "segments" and len(parts) == 4:
                target = f"fl-{parts[3]}" + (f"-{frag}" if frag else "")
            elif parts[1] == "datatypes":
                target = f"dt-{parts[2]}"
            elif parts[1] == "value-sets":
                target = f"vs-{parts[2]}"
            elif parts[1] == "profiles":
                target = f"prof-{parts[2]}"
            elif parts[1] == "coconstraints":
                target = f"cocon-{parts[2]}"
        elif parts[:1] == ["resources"]:
            target = frag or "app-resources"
        elif parts[:1] == ["glossary"]:
            target = frag or "app-glossary"
        elif parts[:1] == ["examples"]:
            target = frag or "app-examples"
        elif parts[:1] == ["err5-codes"]:
            target = frag or "app-err5"
        elif len(parts) == 1:
            target = frag or parts[0]
        if target is None:
            return f'href="{web}{esc(href)}"'
        return f'href="#{target}"'
    return re.sub(r'href="([^"]*)"', repl, fragment)


def pg(target: str) -> str:
    """A page number, filled in once the layout is known."""
    return f'<span class="pg" data-ref="{esc(target)}"></span>'


# =========================================================================== content

class Builder:
    def __init__(self):
        self.guide = read_yaml(DATA_DIR / "guide.yml", {})
        self.web = self.guide.get("site", "")
        self.source = (read_yaml(CARDS_DIR / META / "source.yml", {}) or {}).get("narrative_docx", {})
        roots, _findings, structure = check_cards.run_checks_full(CARDS_DIR, DATA_DIR, REPO / "quality")
        self.roots = roots
        self.cards = list(walk(roots))
        self.by_id = {c.id: c for c in self.cards}
        self.structure = structure or {}
        self.model = Model(REPO / "model") if Model.available(REPO / "model") else None
        self.st = Structure(self.model) if self.model else None
        refs = (read_yaml(DATA_DIR / "references.yml", {}) or {}).get("references", [])
        self.ref_by_num = {r["number"]: r for r in refs}
        ex_data = self.structure.get("examples") or {}
        self.examples = ex_data.get("examples", [])
        self.bases = read_yaml(REPO / "examples" / "_meta" / "bases.yml", {}) or {}
        self.renderer = site_examples.Renderer(self.model, self.bases, ex_data.get("results", {}), self.st)
        self.ex_number = {}  # example id -> "A.3.2"
        self.toc = []  # (level, number, title, anchor)
        self.err5 = site_err5.load(REPO)

    def link(self, fragment: str) -> str:
        if self.st:
            fragment = self.st.autolink(fragment, "")
        return pdf_links(fragment, self.web)

    def heading(self, level: int, number: str, title: str, anchor: str, toc_level: int | None = None, cls: str = "") -> str:
        if toc_level is not None:
            self.toc.append((toc_level, number, title, anchor))
        num = f'<span class="num">{esc(number)}</span> ' if number else ""
        return f'<h{level} id="{esc(anchor)}" class="{cls}" data-bm="{toc_level if toc_level is not None else ""}">{num}{esc(title)}</h{level}>'

    # ------------------------------------------------------------------ front matter
    def cover(self) -> str:
        g = self.guide
        pubs = " and the ".join(esc(p["name"]) for p in g["publishers"])
        today = dt.date.today().strftime("%d %B %Y").lstrip("0")
        return f"""<section class="cover">
<p class="cover-status">{esc(g['status'].upper())}</p>
<p class="cover-eyebrow">{esc(g['release'])}</p>
<h1 class="cover-title">{esc(g['title'])}</h1>
<p class="cover-pubs">A joint publication of the {pubs}</p>
<div class="cover-note"><p><strong>{esc(g.get('status_note', ''))}</strong></p>
<p>PDF edition of {today}, built from narrative draft <code>{esc(self.source.get('file', 'unknown'))}</code>{esc(build_site.git_commit())}.</p>
<p>The guide is published first as a website, where every section has a permanent link and can be commented on:<br>
<a href="{esc(self.web)}">{esc(self.web)}</a></p></div>
</section>"""

    def about(self) -> str:
        n_st = sum(len(c.statements) for c in self.cards)
        return f"""<section class="front" id="about-pdf">
<h2 class="front-h">About this PDF edition</h2>
<p>This PDF has the same content as the website edition of the guide: {len(self.cards)} sections with {n_st} conformance
statements, the message infrastructure generated from the IGAMT conformance export,{f" {len(self.examples)} example messages," if self.examples else ""} and
the appendices. It is arranged to be read in order:</p>
<ul>
<li><strong>Conformance statements</strong> follow the explanation in each section, numbered s1, s2, ... as on the website.
To refer to one, give the section number and the statement number, for example <em>4.2.1 s3</em>. Section numbers can change
between drafts; the web address of each section does not. Each section heading links to its page on the website.</li>
{"" if not self.examples else """<li><strong>Example messages</strong> are collected in Appendix A. A section that has examples lists them by number and page.
Most examples show only the segments they are about; the rest of the message is one of the base messages printed at the start
of the appendix.</li>"""}
<li><strong>Field references</strong> such as RXA-20, profile codes such as Z22, and value set names are links to chapter 7
and Appendix E.</li>
<li><strong>Chapter 7</strong> is organized by message profile, then by segment in message order. Where a segment has more
than one variant (flavor), the main one is shown in full and the others by how they differ from it.</li>
<li><strong>Value sets</strong> are in Appendix E. Code systems that are maintained outside this guide and change often, such as
CVX, MVX, and NDC, and very long tables, are described there without their codes; see the website or the source named.</li>
</ul>
<p>Comments are collected on the website, not on this PDF.</p>
</section>"""

    def toc_html(self) -> str:
        lis = []
        for level, number, title, anchor in self.toc:
            if level > 2:
                continue
            lis.append(f'<li class="toc-l{level}"><a href="#{esc(anchor)}"><span class="toc-num">{esc(number)}</span>'
                       f'<span class="toc-title">{esc(title)}</span>{pg(anchor)}</a></li>')
        return f'<section class="front toc-page" id="toc"><h2 class="front-h">Contents</h2><ol class="toc">{"".join(lis)}</ol></section>'

    # ------------------------------------------------------------------ chapters 1–6
    def card_html(self, c) -> str:
        level = min(c.depth, 5)
        toc_level = c.depth if c.depth <= 4 else None
        parts = []
        head = self.heading(level, c.number, c.title, c.id, toc_level, cls=f"card-h d{c.depth}" + (" chapter" if c.depth == 1 else ""))
        if c.depth == 1:
            parts.append('<section class="chapter-start">')
        web = f"{self.web}{c.id}/index.html"
        head = head.replace(f'{esc(c.title)}</h', f'<a class="web" href="{esc(web)}">{esc(c.title)}</a></h', 1)
        parts.append(head)
        narrative = minimd.render(c.narrative, citation_href="resources/index.html") if c.narrative.strip() else ""
        if narrative:
            parts.append(f'<div class="narrative">{self.link(narrative)}</div>')
        if c.meta.get("glossary"):
            parts.append(self.link(build_site.glossary_html(c.meta["glossary"])))
        if c.statements:
            lis = "".join(
                f'<li id="{esc(s["id"])}"><span class="s-id">{esc(s["id"].rsplit("--", 1)[-1])}</span>'
                f'<span class="verb verb-{build_site.VERB_CLASS.get(s.get("verb", ""), "may")}">{esc(s.get("verb", ""))}</span> '
                f'<span class="s-text">{esc(s["text"])}</span></li>' for s in c.statements)
            parts.append(self.link(f'<section class="statements"><p class="st-h">Conformance statements</p><ol>{lis}</ol></section>'))
        for f in c.meta.get("figures", []):
            label = f"Figure {f['number']}" if f.get("number") is not None else "Figure"
            src = (c.path / f["file"]).resolve().as_uri()
            parts.append(f'<figure id="{esc(f["id"])}"><img src="{src}" alt="{esc(f.get("alt") or f.get("caption") or label)}">'
                         f'<figcaption><strong>{esc(label)}.</strong> {esc(f.get("caption", ""))}</figcaption></figure>')
        tables = build_site.tables_html(c)
        if tables:
            parts.append(self.link(tables))
        exs = [ex for ex in self.examples if c.id in ex.get("cards", [])]
        if exs:
            lis = "".join(f'<li><a href="#ex-{esc(ex["id"])}">{esc(self.ex_number.get(ex["id"], ""))} {esc(ex["title"])}</a>'
                          f'{pg("ex-" + ex["id"])}</li>' for ex in exs)
            parts.append(f'<div class="see-box"><p class="st-h">Example message{"s" if len(exs) > 1 else ""} (Appendix A)</p><ul class="pg-list">{lis}</ul></div>')
        refs = [self.ref_by_num[n] for n in c.meta.get("references", []) if n in self.ref_by_num]
        if refs:
            lis = "".join(f'<li><a href="#ref-{r["number"]}">[{r["number"]}]</a> {esc(r["title"])}</li>' for r in refs)
            parts.append(f'<div class="see-box"><p class="st-h">Resources cited (Appendix C)</p><ul>{lis}</ul></div>')
        if self.err5 and c.id == site_err5.ERR5_CARD:
            parts.append(f'<div class="see-box"><p>The national ERR-5 code set, with each code\'s implementation priority, is in '
                         f'<a href="#app-err5">Appendix D</a>{pg("app-err5")}.</p></div>')
        if not (narrative or c.statements or c.children or c.meta.get("figures") or c.meta.get("glossary")):
            parts.append('<p class="empty">This section has no content in the current draft.</p>')
        if c.depth == 1:
            parts.append("</section>")
        return "\n".join(parts) + "".join(self.card_html(k) for k in c.children)

    # ------------------------------------------------------------------ chapter 7
    def usage(self, el, preds=()) -> str:
        if preds:
            p = preds[0]
            return f'C({esc(p["true_usage"])}/{esc(p["false_usage"])})'
        return esc(el.get("usage") or "")

    def card_range(self, el) -> str:
        return f"[{esc(el['min'])}..{esc(el['max'])}]" if "min" in el else ""

    def bindings(self, el) -> str:
        parts = []
        for b in el.get("bindings", []):
            parts.append(", ".join(f'<a href="#vs-{slug(v)}">{esc(v)}</a>' for v in b["value_sets"]))
        return "<br>".join(parts)

    def dt_ref(self, xml_id: str) -> str:
        if xml_id == "var":
            return "varies"
        d = self.model.datatypes.get(xml_id)
        label = d["label"] if d else xml_id
        return f'<a href="#dt-{slug(xml_id)}">{esc(label)}</a>' if d else esc(label)

    def field_key(self, s, f):
        preds = tuple(sorted(x["description"] for x in s["predicates"] if (x.get("target_path") or "").startswith(f"{f['position']}[")))
        return (f.get("datatype"), f.get("usage"), f.get("min"), f.get("max"), f.get("min_length"), f.get("max_length"),
                tuple(tuple(b["value_sets"]) for b in f.get("bindings", [])), preds)

    def field_rows(self, s, fields, anchor_prefix: str) -> str:
        rows = []
        for f in fields:
            pos = f["position"]
            preds = [x for x in s["predicates"] if (x.get("target_path") or "").startswith(f"{pos}[")]
            lo, hi = f.get("min_length"), f.get("max_length")
            length = "" if lo is None and hi is None else f"{lo if lo is not None else ''}..{hi if hi is not None else ''}"
            rows.append(f'<tr id="{anchor_prefix}-f{pos}"><td class="nowrap">{esc(s["name"])}-{pos}</td><td>{esc(f["name"])}</td>'
                        f'<td>{self.dt_ref(f["datatype"])}</td><td class="nowrap">{self.usage(f, preds)}</td><td class="nowrap">{self.card_range(f)}</td>'
                        f'<td class="nowrap">{esc(length)}</td><td>{self.bindings(f)}</td></tr>')
        return ('<table class="model fields"><thead><tr><th>Field</th><th>Name</th><th>Type</th><th>Usage</th><th>Card.</th>'
                f'<th>Length</th><th>Value set</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')

    def predicates(self, items, prefix) -> str:
        if not items:
            return ""
        rows = "".join(f'<tr><td class="nowrap">{esc(prefix)}{esc(p.get("target") or p.get("target_path"))}</td><td>{esc(p["description"])}</td>'
                       f'<td>{esc(p["true_usage"])}</td><td>{esc(p["false_usage"])}</td></tr>' for p in items)
        return (f'<p class="tbl-h">Conditional usage</p><table class="model"><thead><tr><th>Element</th><th>Condition</th><th>True</th><th>False</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>')

    def constraints(self, items, title="Conformance statements") -> str:
        if not items:
            return ""
        rows = "".join(f'<tr><td class="nowrap">{esc(c["id"])}</td><td>{esc(c["description"])}</td></tr>' for c in items)
        return f'<p class="tbl-h">{esc(title)}</p><table class="model"><thead><tr><th>ID</th><th>Statement</th></tr></thead><tbody>{rows}</tbody></table>'

    def chapter7(self) -> str:
        m, st = self.model, self.st
        n7 = str(len(self.roots) + 1)
        out = ['<section class="chapter-start">', self.heading(1, n7, "Message Infrastructure", "ch7", 1, cls="card-h d1 chapter")]
        export = (read_yaml(m.dir / "source.yml", {}) or {}).get("export", "")
        out.append(f'<p>This chapter is generated from the IGAMT conformance export{f" (<code>{esc(export)}</code>)" if export else ""}. '
                   'IGAMT is the authoritative source for message structure. Usage codes: R required, RE required but may be empty, '
                   'O optional, X not supported, C(a/b) conditional (a when the condition is true, b when it is false; the conditions '
                   'are listed under each table). Value sets are in Appendix E.</p></section>')

        # profiles, each with its co-constraints
        profiles = sorted(m.profiles, key=lambda p: PROFILE_ORDER.index(p["code"]) if p["code"] in PROFILE_ORDER else 99)
        out.append(self.heading(2, f"{n7}.1", "Message profiles", "ch7-profiles", 2, cls="card-h d2"))
        for i, p in enumerate(profiles, 1):
            num = f"{n7}.1.{i}"
            out.append(self.heading(3, num, f"{p['code']} {p['title']}", f"prof-{p['code'].lower()}", 3, cls="card-h d3"))
            out.append(f'<p class="facts">Message type <code>{esc(p["message_type"])}^{esc(p["event"] or "")}^{esc(p["structure"])}</code>. '
                       f'{esc(p.get("description") or "")}</p>')
            rows = []

            def walk_nodes(nodes, depth):
                for n in nodes:
                    pad = f' style="padding-left:{4 + depth * 12}pt"'
                    if n["kind"] == "group":
                        rows.append(f'<tr class="grp"><td{pad}><strong>{esc(n["name"])}</strong> group</td><td>{self.usage(n)}</td>'
                                    f'<td>{self.card_range(n)}</td><td></td></tr>')
                        walk_nodes(n["children"], depth + 1)
                        continue
                    seg = m.segments[n["ref"]]
                    printed = n["ref"] in st.used_flavors
                    seg_ref = f'<a href="#seg-{slug(seg["name"])}">{esc(seg["name"])}</a>' if printed else esc(seg["name"])
                    fl_ref = (f'<a href="#fl-{st.flavor_slug(n["ref"])}">{esc(st.flavor_title(n["ref"]))}</a>' if printed
                              else f'{esc(st.flavor_title(n["ref"]))} <span class="mini">(base HL7)</span>')
                    rows.append(f'<tr><td{pad}>{seg_ref} <span class="mini">{esc(seg.get("description") or "")}</span></td>'
                                f'<td>{self.usage(n)}</td><td>{self.card_range(n)}</td><td>{fl_ref}</td></tr>')
                    for s in [s for s in m.slicings if s["profile"] == p["code"] and s["default_flavor"] == n["ref"]]:
                        for sl in s["slices"]:
                            rows.append(f'<tr class="slice"><td style="padding-left:{16 + depth * 12}pt" colspan="3">'
                                        f'<span class="mini">{esc(sl["when"])}</span></td><td><a href="#fl-{st.flavor_slug(sl["flavor"])}">{esc(sl["flavor"])}</a></td></tr>')
            walk_nodes(p["children"], 0)
            out.append('<table class="model tree"><thead><tr><th>Segment or group</th><th>Usage</th><th>Card.</th><th>Flavor</th></tr></thead>'
                       f'<tbody>{"".join(rows)}</tbody></table>')
            group_cons = []

            def gwalk(nodes, trail):
                for n in nodes:
                    if n["kind"] == "group":
                        group_cons.extend({**c, "description": f"[{'.'.join(trail + [n['name']])}] " + c["description"]} for c in n["constraints"])
                        gwalk(n["children"], trail + [n["name"]])
            gwalk(p["children"], [])
            out.append(self.constraints(p["constraints"], "Message-level conformance statements"))
            out.append(self.constraints(group_cons, "Group-level conformance statements"))
            out.append(self.cocon(p["code"], num))

        # segments, in message order
        names = sorted({m.segments[l]["name"] for l in st.used_flavors},
                       key=lambda n: (SEGMENT_ORDER.index(n) if n in SEGMENT_ORDER else 99, n))
        out.append(self.heading(2, f"{n7}.2", "Segments", "ch7-segments", 2, cls="card-h d2 page-break"))
        for i, name in enumerate(names, 1):
            flavors = [s for s in m.segments.values() if s["name"] == name and s["label"] in st.used_flavors]
            flavors.sort(key=lambda s: (-len([pl for pl in st.placements_by_flavor[s["label"]] if not pl["excluded"]]), "COCON" in s["label"], s["label"]))
            main = flavors[0]
            desc = main.get("description") or ""
            out.append(self.heading(3, f"{n7}.2.{i}", f"{name} {desc}", f"seg-{slug(name)}", 3, cls="card-h d3"))
            # field anchors used by the narrative (seg-rxa-f20) land on the main flavor's rows
            for f in main["fields"]:
                out.append(f'<a id="seg-{slug(name)}-f{f["position"]}"></a>')
            for s in flavors:
                profs = sorted({pl["profile"] for pl in st.placements_by_flavor[s["label"]] if not pl["excluded"]},
                               key=lambda c: PROFILE_ORDER.index(c) if c in PROFILE_ORDER else 99)
                anchor = f"fl-{st.flavor_slug(s['label'])}"
                title = st.flavor_title(s["label"])
                used = f'Used in {", ".join(profs)}.' if profs else ""
                if s is main or len(flavors) == 1:
                    out.append(f'<h4 id="{anchor}" class="flavor-h">{esc(title)}</h4><p class="mini">{esc(used)}</p>')
                    out.append(self.field_rows(s, s["fields"], anchor))
                else:
                    base = {f["position"]: self.field_key(main, f) for f in main["fields"]}
                    diff = [f for f in s["fields"] if base.get(f["position"]) != self.field_key(s, f)]
                    out.append(f'<h4 id="{anchor}" class="flavor-h">{esc(title)}</h4><p class="mini">{esc(used)} '
                               f'Same as {esc(st.flavor_title(main["label"]))} except for the {len(diff)} field{"s" if len(diff) != 1 else ""} below.</p>')
                    if diff:
                        out.append(self.field_rows(s, diff, anchor))
                    for f in s["fields"]:
                        if f not in diff:
                            out.append(f'<a id="{anchor}-f{f["position"]}"></a>')
                out.append(self.predicates(s["predicates"], name + "-"))
                out.append(self.constraints(s["constraints"]))

        # data types: the flavors constrained for this guide in full, base types in one table
        dts = sorted(m.datatypes.values(), key=lambda d: (d["label"], d["xml_id"]))
        constrained = [d for d in dts if d["xml_id"] != d["name"] or d["constraints"] or d["predicates"]]
        base = [d for d in dts if d not in constrained]
        out.append(self.heading(2, f"{n7}.3", "Data types", "ch7-datatypes", 2, cls="card-h d2 page-break"))
        out.append("<p>The data types constrained for this guide are shown in full. The base HL7 data types they use, unchanged, are listed "
                   f'in <a href="#ch7-base-dt">{n7}.3.{len(constrained) + 1}</a>.</p>')
        for i, d in enumerate(constrained, 1):
            title = d["label"] + (f" (HL7 {d['version']})" if d["xml_id"] != d["label"] else "")
            out.append(self.heading(3, f"{n7}.3.{i}", f"{title} {d.get('description') or ''}", f"dt-{slug(d['xml_id'])}", None, cls="card-h d3 dt-h"))
            rows = []
            for k, c in enumerate(d["components"], 1):
                preds = [x for x in d["predicates"] if (x.get("target_path") or "").startswith(f"{k}[")]
                lo, hi = c.get("min_length"), c.get("max_length")
                length = "" if lo is None and hi is None else f"{lo if lo is not None else ''}..{hi if hi is not None else ''}"
                rows.append(f'<tr><td class="nowrap">{esc(d["name"])}.{k}</td><td>{esc(c["name"])}</td><td>{self.dt_ref(c["datatype"])}</td>'
                            f'<td class="nowrap">{self.usage(c, preds)}</td><td class="nowrap">{esc(length)}</td><td>{self.bindings(c)}</td></tr>')
            if rows:
                out.append('<table class="model fields"><thead><tr><th>Comp.</th><th>Name</th><th>Type</th><th>Usage</th><th>Length</th>'
                           f'<th>Value set</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')
            out.append(self.predicates(d["predicates"], d["name"] + "."))
            out.append(self.constraints(d["constraints"]))
        out.append(self.heading(3, f"{n7}.3.{len(constrained) + 1}", "Base HL7 data types", "ch7-base-dt", None, cls="card-h d3"))
        rows = "".join(
            f'<tr id="dt-{slug(d["xml_id"])}"><td class="nowrap">{esc(d["label"])}</td><td>{esc(d.get("description") or "")}</td>'
            f'<td>{esc(", ".join(c["name"] for c in d["components"])) or "<span class=mini>primitive</span>"}</td></tr>' for d in base)
        out.append(f'<table class="model"><thead><tr><th>Type</th><th>Name</th><th>Components</th></tr></thead><tbody>{rows}</tbody></table>')
        return "\n".join(out)

    def cocon(self, code: str, num: str) -> str:
        tables = [t for t in self.model.coconstraints if t["profile"] == code]
        if not tables:
            return ""
        out = [f'<h4 id="cocon-{code.lower()}" class="flavor-h">{esc(code)} OBX co-constraints</h4>',
               f'<p class="mini">Which observations (OBX-3) may appear in each kind of order group, with their value type (OBX-2) and value '
               f'set (OBX-5). Applies at {", ".join(esc(t["location"]) for t in tables)}.</p>']
        n = 0
        for t in tables:
            for tab in t["tables"]:
                n += 1
                cond = tab.get("condition") or "Always"
                rows = []

                def row(r, ind=""):
                    loinc = next((w.get("code") for w in r["when"] if w.get("code")), "")
                    obx2 = ", ".join(th.get("value", "") for th in r["then"] if th["field"] == "OBX-2" and th.get("value"))
                    obx5 = "<br>".join(", ".join(f'<a href="#vs-{slug(x)}">{esc(x)}</a>' for x in th.get("value_sets", []))
                                       for th in r["then"] if th["field"] == "OBX-5")
                    return (f'<tr><td class="nowrap">{ind}{esc(loinc)}</td><td>{esc(r["usage"])}</td><td>[{esc(r["min"])}..{esc(r["max"])}]</td>'
                            f'<td>{esc(obx2)}</td><td>{obx5}</td></tr>')
                rows += [row(r) for r in tab["rows"]]
                for g in tab.get("groups", []):
                    rows.append(f'<tr class="grp"><td colspan="5"><strong>{esc(g["name"])}</strong> · {esc(g["usage"])} [{esc(g["min"])}..{esc(g["max"])}]</td></tr>')
                    rows += [row(r, "↳ ") for r in g["rows"]]
                gb = f' Grouped by {esc(", ".join(tab["group_by"]))}.' if tab.get("group_by") else ""
                out.append(f'<p class="tbl-h">Table {n}. When: {esc(cond)}.{gb}</p><table class="model"><thead><tr><th>OBX-3 (LOINC)</th>'
                           f'<th>Usage</th><th>Card.</th><th>OBX-2</th><th>OBX-5 value set</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')
        return "".join(out)

    # ------------------------------------------------------------------ appendices
    def number_examples(self):
        groups: dict[str, list] = {}
        for ex in self.examples:
            if ex.get("kind") == "base":
                continue
            sec = (ex.get("list") or {}).get("section") or "Other examples"
            groups.setdefault(sec, []).append(ex)
        order = site_examples.SECTION_ORDER + [g for g in groups if g not in site_examples.SECTION_ORDER]
        self.ex_groups = [(g, groups[g]) for g in order if g in groups]
        for gi, (_, exs) in enumerate(self.ex_groups, 2):
            for k, ex in enumerate(exs, 1):
                self.ex_number[ex["id"]] = f"A.{gi}.{k}"
        base_ex = {ex.get("messages", [{}])[0].get("clip", "").strip(): ex for ex in self.examples if ex.get("kind") == "base"}
        self.base_alias = {}
        for i, (key, msg) in enumerate(self.bases.items(), 1):
            self.ex_number[f"base-{key}"] = f"A.1.{i}"
            ex = base_ex.get(str(msg).strip())
            if ex:
                self.ex_number[ex["id"]] = f"A.1.{i}"
                self.base_alias[key] = ex
        for ex in self.examples:  # a base example that is not one of the bases
            if ex["id"] not in self.ex_number:
                self.ex_number[ex["id"]] = "A"

    def message_block(self, segs: list[str]) -> str:
        lines = "".join(f'<span class="seg">{esc(s)}</span>' for s in segs)
        return f'<pre class="hl7">{lines}</pre>'

    def appendix_a(self) -> str:
        out = ['<section class="chapter-start">', self.heading(1, "A", "Example Messages", "app-examples", 1, cls="card-h d1 chapter"),
               "<p>Draft example messages, checked against the IGAMT profiles on every build. Most examples were drafted as clips: only the "
               "segments the example is about. They are printed that way here; the rest of the message is the base message named, printed "
               "in full in A.1. Long segments wrap; a segment always starts at the left margin.</p></section>"]
        out.append(self.heading(2, "A.1", "Base messages", "ex-bases", 2, cls="card-h d2"))
        names = {"vxu-base": "VXU base message (Z22)", "rsp-base": "RSP base message (Z32/Z42)", "ack-base": "ACK base message (Z23)"}
        for key, msg in self.bases.items():
            ex = self.base_alias.get(key)
            alias = f'<a id="ex-{esc(ex["id"])}"></a>' if ex else ""
            title = names.get(key, key)
            out.append(f'<div class="example">{alias}{self.heading(3, self.ex_number[f"base-{key}"], title, f"base-{key}", None, cls="ex-h")}')
            out.append(self.message_block(hl7msg.segments(str(msg))) + "</div>")
        for gi, (g, exs) in enumerate(self.ex_groups, 2):
            out.append(self.heading(2, f"A.{gi}", g, f"ex-group-{gi}", 2, cls="card-h d2"))
            for ex in exs:
                out.append(self.example(ex))
        return "\n".join(out)

    def example(self, ex) -> str:
        parts = [f'<div class="example" id="ex-{esc(ex["id"])}">',
                 self.heading(3, self.ex_number[ex["id"]], ex["title"], f"exh-{ex['id']}", None, cls="ex-h")]
        meta = []
        if ex.get("profile"):
            meta.append(f'Profile <a href="#prof-{ex["profile"].lower()}">{esc(ex["profile"])}</a>')
        cards = [self.by_id[c] for c in ex.get("cards", []) if c in self.by_id]
        if cards:
            meta.append("Illustrates " + "; ".join(f'<a href="#{c.id}">{esc(c.number)} {esc(c.title)}</a>{pg(c.id)}' for c in cards))
        if meta:
            parts.append(f'<p class="mini">{". ".join(meta)}.</p>')
        parts += [self.link(f"<p>{esc(n)}</p>") for n in ex.get("notes", [])]
        for m in ex["messages"]:
            if m.get("label") and m["label"] not in ex["title"]:
                parts.append(self.link(f'<p class="ex-label">{esc(m["label"])}</p>'))
            segs = hl7msg.segments(m["message"])
            from_clip = m.get("from_clip") or []
            if m.get("base") and from_clip and len(from_clip) < len(segs):
                parts.append(self.message_block([segs[i] for i in from_clip]))
                b = m["base"]
                parts.append(f'<p class="mini">With the other segments of the <a href="#base-{esc(b)}">{esc(self.ex_number.get("base-" + b, b))} base message</a>.</p>')
            else:
                parts.append(self.message_block(segs))
        parts.append("</div>")
        return "".join(parts)

    def appendix_b(self) -> str:
        gl = read_yaml(DATA_DIR / "glossary.yml", {}) or {}
        titles = {norm_title(c.title): c for c in self.cards}

        def see(text: str) -> str:
            def repl(m):
                names = re.split(r",\s*|\s+and\s+", m.group(1))
                linked = []
                for n in names:
                    c = titles.get(norm_title(n))
                    linked.append(f'<a href="#{c.id}">{esc(n)}</a> ({esc(c.number)}{pg(c.id)})' if c else esc(n))
                return "See " + ", ".join(linked) + "."
            return re.sub(r"See ([^.]+)\.", repl, text)

        out = ['<section class="chapter-start">', self.heading(1, "B", "Glossary and Abbreviations", "app-glossary", 1, cls="card-h d1 chapter"),
               minimd.render(gl.get("intro", "")), "</section>"]
        for i, g in enumerate(gl.get("groups", []), 1):
            out.append(self.heading(2, f"B.{i}", g["name"], f"gl-{i}", 2, cls="card-h d2"))
            out.append("<dl class='terms'>")
            for e in g.get("entries", []):
                anchor = "term-" + re.sub(r"[^a-z0-9]+", "-", e["term"].lower()).strip("-")
                out.append(f"<dt id='{anchor}'>{esc(e['term'])}</dt><dd>{see(esc(e['definition']))}</dd>")
            out.append("</dl>")
        return "\n".join(out)

    def appendix_c(self) -> str:
        rd = read_yaml(DATA_DIR / "references.yml", {}) or {}
        out = ['<section class="chapter-start">', self.heading(1, "C", "Resources", "app-resources", 1, cls="card-h d1 chapter"),
               minimd.render(rd.get("intro", "")), "</section>"]
        current, gi = None, 0
        for r in rd.get("references", []):
            if r.get("group") != current:
                current = r.get("group")
                gi += 1
                g = next((x for x in rd.get("groups", []) if x["name"] == current), {})
                out.append(self.heading(2, f"C.{gi}", current or "", f"res-{gi}", 2, cls="card-h d2"))
                if g.get("description"):
                    out.append(f"<p>{esc(g['description'])}</p>")
            url = f'<br><a class="url" href="{esc(r["url"])}">{esc(r["url"])}</a>' if r.get("url") else ""
            out.append(f'<p class="ref" id="ref-{r["number"]}"><span class="ref-n">[{r["number"]}]</span> <strong>{esc(r["title"])}</strong>'
                       f'{url}<br>{esc(r.get("description", ""))}</p>')
        return "\n".join(out)

    def appendix_d(self) -> str:
        if not self.err5:
            return ""
        page = site_err5.page(self.err5, "", self.by_id)
        page = re.sub(r'<p class="eyebrow">Appendix D</p>\s*<h1>[^<]*</h1>', "", page)
        page = re.sub(r"<h2>", '<h3 class="card-h d3">', page).replace("</h2>", "</h3>")
        page = page.replace('<article class="page err5-page">', '<div class="err5-page">').replace("</article>", "</div>")
        self.toc.append((1, "D", "National ERR-5 Application Error Codes", "app-err5"))
        return ('<section class="chapter-start">' + '<h1 id="app-err5" class="card-h d1 chapter" data-bm="1"><span class="num">D</span> '
                'National ERR-5 Application Error Codes</h1></section>' + self.link(page))

    def appendix_e(self) -> str:
        m, st = self.model, self.st
        vss = sorted((v for v in m.value_sets.values() if v["id"] in st.bound_at), key=lambda v: v["id"].lower())
        unbound = [v for v in m.value_sets.values() if v["id"] not in st.bound_at]
        out = ['<section class="chapter-start">', self.heading(1, "E", "Value Sets", "app-value-sets", 1, cls="card-h d1 chapter"),
               f"<p>The {len(vss)} value sets bound to an element in the message profiles, from the IGAMT export, in alphabetical order. "
               f"Code systems maintained outside this guide that change often (dynamic value sets with more than 40 codes) and tables of more "
               f"than {LIST_LIMIT} codes are described but their codes are not printed: use the current release from the source named, "
               f"or the website edition.{f' {len(unbound)} value set(s) in the export are not bound to any element and are left out.' if unbound else ''}</p></section>"]
        rows = "".join(f'<tr><td><a href="#vs-{slug(v["id"])}">{esc(v["id"])}</a></td><td>{esc(v.get("name") or "")}</td>'
                       f'<td class="n">{len(v["codes"])}</td><td class="nowrap">{pg("vs-" + slug(v["id"]))}</td></tr>' for v in vss)
        out.append(self.heading(2, "E.1", "Index of value sets", "vs-index", 2, cls="card-h d2"))
        out.append(f'<table class="model vs-index"><thead><tr><th>ID</th><th>Name</th><th>Codes</th><th>Page</th></tr></thead><tbody>{rows}</tbody></table>')
        out.append(self.heading(2, "E.2", "Value set definitions", "vs-defs", 2, cls="card-h d2 page-break"))
        for v in vss:
            codes = v["codes"]
            omit = len(codes) > LIST_LIMIT or (v.get("stability") == "Dynamic" and len(codes) > 40)
            systems = {c.get("system") or "" for c in codes}
            one_system = len(systems) == 1
            facts = [f'{esc(v.get("stability") or "")}, {esc((v.get("extensibility") or "").lower())}', f"{len(codes)} codes"]
            if one_system and codes:
                facts.append(f"code system {esc(next(iter(systems)))}")
            ext = v.get("external") or {}
            if ext:
                facts.append("source: " + esc(", ".join(f"{k} {x}" for k, x in ext.items())))
            bound = st.bound_at.get(v["id"], [])
            bound_txt = "; ".join(esc(label) for label, _ in bound[:6]) + (f"; and {len(bound) - 6} more" if len(bound) > 6 else "")
            body = [f'<div class="vs" id="vs-{slug(v["id"])}"><h4 class="vs-h">{esc(v["id"])} <span class="vs-name">{esc(v.get("name") or "")}</span></h4>',
                    f'<p class="mini">{" · ".join(facts)}. Bound to {bound_txt}.</p>']
            if v.get("description") and v["description"] != v.get("name"):
                body.append(f'<p class="vs-desc">{esc(v["description"])}</p>')
            if omit:
                body.append(f'<p class="omitted">Codes not printed ({len(codes)} in the export). Use the current release from the maintainer of '
                            f'this code system, or the website edition.</p>')
            elif codes:
                has_usage = any(c.get("usage") for c in codes)
                has_comments = any(c.get("comments") for c in codes)
                head = ("<th>Code</th><th>Display name</th>" + ("" if one_system else "<th>System</th>")
                        + ("<th>Usage</th>" if has_usage else "") + ("<th>Comments</th>" if has_comments else ""))
                rows = "".join(
                    f'<tr><td class="code">{esc(c["code"])}</td><td>{esc(c.get("display") or "")}</td>'
                    + ("" if one_system else f'<td>{esc(c.get("system") or "")}</td>')
                    + (f'<td>{esc(c.get("usage") or "")}</td>' if has_usage else "")
                    + (f'<td class="mini">{esc(c.get("comments") or "")}</td>' if has_comments else "") + "</tr>" for c in codes)
                cls = "codes cols2" if not (has_comments or not one_system) and len(codes) > 12 else "codes"
                body.append(f'<table class="model {cls}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')
            body.append("</div>")
            out.append("".join(body))
        return "\n".join(out)

    # ------------------------------------------------------------------ whole document
    def document(self) -> str:
        self.number_examples()
        chapters = "\n".join(self.card_html(r) for r in self.roots)
        ch7 = self.chapter7() if self.model else ""
        # Appendix A is left out while the examples are hidden (data/guide.yml examples.show); B-E keep their letters
        apps = [self.appendix_a() if self.examples else "", self.appendix_b(), self.appendix_c(), self.appendix_d(), self.appendix_e() if self.model else ""]
        body = "\n".join([chapters, ch7, *apps])
        css = (PDF_SRC / "print.css").read_text(encoding="utf-8")
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{esc(self.guide['title'])}, {esc(self.guide['release'])} ({esc(self.guide['status'])})</title>
<style>{css}</style></head>
<body>
{self.cover()}
{self.about()}
{self.toc_html()}
<main>{body}</main>
</body></html>"""


# =========================================================================== rendering

def find_chrome(explicit: str | None) -> str:
    for c in ([explicit] if explicit else CHROME_CANDIDATES):
        if c and (Path(c).exists() or shutil.which(c)):
            return c if Path(c).exists() else shutil.which(c)
    raise SystemExit("Chrome or Edge not found; pass --chrome")


def print_pdf(chrome: str, html_path: Path, pdf_path: Path) -> None:
    profile = html_path.parent / ".chrome-profile"
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
           f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    if not pdf_path.exists():
        raise SystemExit(f"Chrome did not write {pdf_path}")


def anchor_pages(pdf_path: Path) -> dict[str, int]:
    """Named destinations (one per id that is a link target) → 1-based page number."""
    import pymupdf
    with pymupdf.open(pdf_path) as doc:
        names = doc.resolve_names()
    return {k: v["page"] + 1 for k, v in names.items() if v.get("page", -1) >= 0}


def fill_pages(doc_html: str, pages: dict[str, int]) -> str:
    def repl(m):
        n = pages.get(html.unescape(m.group(1)))
        return f'<span class="pg" data-ref="{m.group(1)}">{n if n else "?"}</span>'
    return re.sub(r'<span class="pg" data-ref="([^"]*)">[^<]*</span>', repl, doc_html)


def finish(pdf_in: Path, pdf_out: Path, toc: list, pages: dict[str, int], guide: dict) -> None:
    """Running heads, page numbers, and bookmarks."""
    import pymupdf
    doc = pymupdf.open(pdf_in)
    n = doc.page_count
    chapters = sorted(((pages[a], f"{num} {title}".strip()) for level, num, title, a in toc if level == 1 and a in pages))
    status = guide.get("status", "Draft").upper()
    short = guide.get("short_title", "")
    for i, page in enumerate(doc, 1):
        if i == 1:
            continue
        w, h = page.rect.width, page.rect.height
        current = ""
        for p, t in chapters:
            if p <= i:
                current = t
        grey = (0.35, 0.42, 0.48)
        page.insert_text((54, 34), f"{short}", fontsize=7.5, fontname="helv", color=grey)
        if current:
            tw = pymupdf.get_text_length(current, fontname="helv", fontsize=7.5)
            page.insert_text((w - 54 - tw, 34), current, fontsize=7.5, fontname="helv", color=grey)
        foot = f"{status}: {guide.get('status_note', '')}"
        page.insert_text((54, h - 26), foot, fontsize=7.5, fontname="helv", color=(0.6, 0.15, 0.1))
        num = f"Page {i} of {n}"
        tw = pymupdf.get_text_length(num, fontname="helv", fontsize=7.5)
        page.insert_text((w - 54 - tw, h - 26), num, fontsize=7.5, fontname="helv", color=grey)
    outline = [[1, "Cover", 1], [1, "About this PDF edition", pages.get("about-pdf", 2)], [1, "Contents", pages.get("toc", 3)]]
    last = 1
    for level, num, title, a in toc:
        if a not in pages:
            continue
        level = min(level, last + 1)
        outline.append([level, f"{num} {title}".strip(), pages[a]])
        last = level
    doc.set_toc(outline)
    doc.set_metadata({"title": f"{guide['title']}, {guide['release']} ({guide['status']})",
                      "author": " and ".join(p["name"] for p in guide["publishers"]), "subject": guide.get("status_note", "")})
    doc.save(pdf_out, garbage=3, deflate=True)
    doc.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=REPO / "output" / "pdf")
    parser.add_argument("--chrome")
    args = parser.parse_args(argv)
    chrome = find_chrome(args.chrome)
    args.out.mkdir(parents=True, exist_ok=True)
    b = Builder()
    doc_html = b.document()
    html_path = args.out / "guide.html"
    raw = args.out / "pass.pdf"
    pages: dict[str, int] = {}
    for attempt in range(3):  # page numbers can push text onto the next page; repeat until stable
        write_text(html_path, fill_pages(doc_html, pages))
        if raw.exists():
            raw.unlink()
        print_pdf(chrome, html_path, raw)
        new = anchor_pages(raw)
        stable = all(new.get(k) == pages.get(k) for k in re.findall(r'data-ref="([^"]*)"', doc_html))
        pages = new
        if stable and attempt:
            break
    refs = set(re.findall(r'href="#([^"]+)"', doc_html))
    ids = set(re.findall(r'id="([^"]+)"', doc_html)) | set(re.findall(r"id='([^']+)'", doc_html))
    missing = sorted(refs - ids)
    name = f"cdc-hl7-v2-guide-r2-{b.guide.get('status', 'draft').lower()}.pdf"
    finish(raw, args.out / name, b.toc, pages, b.guide)
    raw.unlink()
    shutil.rmtree(args.out / ".chrome-profile", ignore_errors=True)
    import pymupdf
    with pymupdf.open(args.out / name) as d:
        print(f"Wrote {args.out / name}: {d.page_count} pages")
    if missing:
        print(f"{len(missing)} internal link target(s) missing, e.g. {', '.join(missing[:8])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
