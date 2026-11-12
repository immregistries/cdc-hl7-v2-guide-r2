"""Chapter 7, Message Infrastructure: pages generated from model/ (the normalized IGAMT export).

Used by build_site.py. Page layout (all under structure/):

    index.html                          chapter overview
    profiles/<z22>/                     message profile: segment tree, slicing, constraints, co-constraints link
    segments/<rxa>/                     segment overview: every field across all flavors of the segment
    segments/<rxa>/<rxa-iz01-adm>/      one segment flavor: fields, predicates, bindings, constraints
    datatypes/<cwe-iz01>/               data type flavor: components, predicates, bindings, constraints
    value-sets/<hl70322-iz01>/          value set: metadata, codes, where it is bound
    coconstraints/<z22>/                OBX co-constraint tables for a profile

IGAMT stays authoritative: these pages only present the export.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict

from guidecards import write_text
from structure_index import FIELD_RE, PROFILE_ORDER, Model

COCON_RE = re.compile(r"^(?P<base>[A-Z0-9]+_[A-Z0-9]+)_COCON.*_(?P<msg>[0-9a-f]{24})$")
USAGE_HELP = {"R": "Required", "RE": "Required, may be empty", "O": "Optional", "C": "Conditional", "X": "Not supported",
              "S": "Usage 'S' (not defined in the guide)", "CE": "Conditional, may be empty"}


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def slug(text: str) -> str:
    """URL path segment. The export has a withdrawn data type whose ID is '-'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or ("withdrawn" if text == "-" else "x")


class Structure:
    def __init__(self, model: Model):
        self.m = model
        self.msg_code = {p["igamt_id"]: p["code"] for p in model.profiles}
        self.placements_by_flavor = defaultdict(list)
        for pl in model.placements:
            self.placements_by_flavor[pl["flavor"]].append(pl)
        self.used_flavors = {f for f, pls in self.placements_by_flavor.items() if any(not p["excluded"] for p in pls)}
        self.bound_at = self._bound_at()

    # ------------------------------------------------------------ addresses
    def flavor_slug(self, label: str) -> str:
        m = COCON_RE.match(label)
        if m:
            return slug(m.group("base")) + "-" + self.msg_code.get(m.group("msg"), "x").lower()
        return slug(label.replace("#", ""))

    def flavor_title(self, label: str) -> str:
        m = COCON_RE.match(label)
        if m:
            return f"{m.group('base')} ({self.msg_code.get(m.group('msg'), '?')} co-constraint flavor)"
        return label

    def flavor_href(self, label: str, root: str) -> str:
        seg = self.m.segments[label]
        return f"{root}structure/segments/{slug(seg['name'])}/{self.flavor_slug(label)}/index.html"

    def segment_href(self, name: str, root: str, field: int | None = None) -> str:
        return f"{root}structure/segments/{slug(name)}/index.html" + (f"#f{field}" if field else "")

    def dt_href(self, xml_id: str, root: str) -> str | None:
        return f"{root}structure/datatypes/{slug(xml_id)}/index.html" if xml_id in self.m.datatypes else None

    def vs_href(self, vid: str, root: str) -> str | None:
        return f"{root}structure/value-sets/{slug(vid)}/index.html" if vid in self.m.value_sets else None

    def profile_href(self, code: str, root: str) -> str:
        return f"{root}structure/profiles/{code.lower()}/index.html"

    def cocon_href(self, code: str, root: str) -> str:
        return f"{root}structure/coconstraints/{code.lower()}/index.html"

    # ------------------------------------------------------------ indexes
    def _bound_at(self) -> dict[str, list[tuple[str, str]]]:
        """value set id → [(label, href-path relative to site root)]"""
        out = defaultdict(list)
        for s in self.m.segments.values():
            for f in s["fields"]:
                for b in f.get("bindings", []):
                    for v in b["value_sets"]:
                        out[v].append((f"{self.flavor_title(s['label'])} {s['name']}-{f['position']}" + (f".{b['path']}" if b.get("path") else ""),
                                       self.flavor_href(s["label"], "") + f"#f{f['position']}"))
        for d in self.m.datatypes.values():
            for i, c in enumerate(d["components"], 1):
                for b in c.get("bindings", []):
                    for v in b["value_sets"]:
                        out[v].append((f"{d['label']}.{i} ({c['name']})", self.dt_href(d["xml_id"], "") + f"#c{i}"))
        for t in self.m.coconstraints:
            for tab in t["tables"]:
                rows = list(tab["rows"]) + [r for g in tab.get("groups", []) for r in g["rows"]]
                for r in rows:
                    loinc = next((w.get("code") for w in r["when"] if w.get("code")), "?")
                    for th in r["then"]:
                        for v in th.get("value_sets", []):
                            out[v].append((f"{t['profile']} OBX-5 when OBX-3 = {loinc}", self.cocon_href(t["profile"], "")))
        return {k: sorted(set(v)) for k, v in out.items()}

    # ------------------------------------------------------------ fragments
    def usage_html(self, el: dict, preds: list[dict]) -> str:
        u = el.get("usage") or ""
        if preds:
            p = preds[0]
            return (f'<abbr class="usage u-C" title="{esc(p["description"])}">C({esc(p["true_usage"])}/{esc(p["false_usage"])})</abbr>')
        return f'<abbr class="usage u-{esc(u)}" title="{esc(USAGE_HELP.get(u, u))}">{esc(u)}</abbr>'

    def card_html(self, el: dict) -> str:
        if "min" not in el:
            return ""
        return f"[{esc(el.get('min'))}..{esc(el.get('max'))}]"

    def length_html(self, el: dict) -> str:
        lo, hi = el.get("min_length"), el.get("max_length")
        if lo is None and hi is None:
            return ""
        return f"{esc(lo if lo is not None else '')}..{esc(hi if hi is not None else '')}"

    def dt_link(self, xml_id: str, root: str) -> str:
        if xml_id == "var":
            return '<span title="Determined by OBX-2">varies</span>'
        href = self.dt_href(xml_id, root)
        label = self.m.datatypes[xml_id]["label"] if xml_id in self.m.datatypes else xml_id
        return f'<a href="{href}"><code>{esc(label)}</code></a>' if href else f"<code>{esc(label)}</code>"

    def vs_link(self, vid: str, root: str) -> str:
        href = self.vs_href(vid, root)
        return f'<a href="{href}"><code>{esc(vid)}</code></a>' if href else f"<code>{esc(vid)}</code>"

    def bindings_html(self, el: dict, root: str) -> str:
        parts = []
        for b in el.get("bindings", []):
            where = f"{b['path']}: " if b.get("path") else ""
            parts.append(where + ", ".join(self.vs_link(v, root) for v in b["value_sets"])
                         + (f' <span class="mini">({esc(b["strength"])})</span>' if b.get("strength") else ""))
        return "<br>".join(parts)

    def constraints_html(self, items: list[dict], title: str = "Conformance statements") -> str:
        if not items:
            return ""
        rows = "".join(
            f'<tr id="cs-{esc(slug(c["id"]))}"><td><code>{esc(c["id"])}</code></td><td>{esc(c.get("strength") or "")}</td>'
            f'<td>{esc(c["description"])}</td></tr>' for c in items)
        return (f'<section><h2>{esc(title)}</h2><div class="table-wrap"><table class="model"><thead><tr><th>ID</th><th>Strength</th>'
                f'<th>Statement</th></tr></thead><tbody>{rows}</tbody></table></div></section>')

    def predicates_html(self, items: list[dict], prefix: str) -> str:
        if not items:
            return ""
        rows = "".join(
            f'<tr><td><code>{esc(prefix)}{esc(p.get("target") or p.get("target_path"))}</code></td>'
            f'<td>{esc(p["description"])}</td><td>{esc(p["true_usage"])}</td><td>{esc(p["false_usage"])}</td></tr>' for p in items)
        return (f'<section><h2>Conditional usage (predicates)</h2><div class="table-wrap"><table class="model"><thead><tr><th>Element</th>'
                f'<th>Condition</th><th>If true</th><th>If false</th></tr></thead><tbody>{rows}</tbody></table></div></section>')

    # ------------------------------------------------------------ autolinks in narrative HTML
    def autolink(self, html_text: str, root: str) -> str:
        """Link field references (RXA-20), profile codes (Z22), and value set IDs in rendered HTML,
        outside tags and existing links."""
        vs_ids = {v for v in self.m.value_sets if re.match(r"^(PHVS_|HL7\d{4}|CVX_|MVX_|NIP\d)", v)}
        profiles = {p["code"] for p in self.m.profiles}
        out, depth = [], 0
        for part in re.split(r"(<[^>]+>)", html_text):
            if part.startswith("<"):
                if re.match(r"<a[\s>]", part):
                    depth += 1
                elif part.startswith("</a"):
                    depth = max(0, depth - 1)
                out.append(part)
                continue
            if depth or not part:
                out.append(part)
                continue

            def field(m):
                seg, pos = m.group(1), int(m.group(2))
                if seg not in self.m.segment_names or not self.m.field_exists(seg, pos):
                    return m.group(0)
                return f'<a class="sref" href="{self.segment_href(seg, root, pos)}" title="{esc(self.m.field_name(seg, pos))}">{m.group(0)}</a>'

            part = FIELD_RE.sub(field, part)
            # profile codes and value set ids (skip text already inside the links just added)
            pieces = re.split(r"(<a [^>]*>.*?</a>)", part)
            for i, piece in enumerate(pieces):
                if piece.startswith("<a "):
                    continue
                piece = re.sub(r"\b(Z\d{2})\b", lambda m: (f'<a class="sref" href="{self.profile_href(m.group(1), root)}">{m.group(1)}</a>'
                                                          if m.group(1) in profiles else m.group(0)), piece)
                piece = re.sub(r"\b([A-Za-z0-9_]{5,})\b", lambda m: (f'<a class="sref" href="{self.vs_href(m.group(1), root)}">{m.group(1)}</a>'
                                                                     if m.group(1) in vs_ids else m.group(0)), piece)
                pieces[i] = piece
            out.append("".join(pieces))
        return "".join(out)


# =========================================================================== pages

def build(out, model: Model, *, shell, findings_panel, field_cards: dict, profile_cards: dict, findings: list[dict], by_id: dict) -> list[dict]:
    """Write all structure pages; return navigation children for chapter 7."""
    st = Structure(model)
    m = model
    root2, root4 = "../", "../../../"  # structure/index.html; structure/<kind>/<name>/index.html
    model_findings = defaultdict(list)
    for f in findings:
        loc = f.get("location") or ""
        if loc.startswith("model:"):
            model_findings[_finding_page(st, loc[6:])].append(f)
    general_findings = model_findings.pop(None, [])

    def page(path, title, body, root, items=None):
        panel = findings_panel(items or [], root, {}) if items else ""
        body = body.replace("<!--findings-->", panel)
        write_text(out / path / "index.html", shell(root=root, title=title, body=body))

    def crumbs(root, *links):
        parts = [f'<a href="{root}index.html">Home</a>', f'<a href="{root}structure/index.html">7 Message Infrastructure</a>']
        parts += [f'<a href="{href}">{esc(t)}</a>' for t, href in links]
        return '<nav class="crumbs" aria-label="Breadcrumb">' + " <span>›</span> ".join(parts) + "</nav>"

    def cards_list(card_ids, root, heading="Discussed in"):
        cs = [by_id[c] for c in dict.fromkeys(card_ids) if c in by_id]
        if not cs:
            return ""
        lis = "".join(f'<li><a href="{root}{c.id}/index.html"><span class="num">{esc(c.number)}</span> {esc(c.title)}</a></li>' for c in cs)
        return f'<section class="related"><h2>{esc(heading)}</h2><ul>{lis}</ul></section>'

    profiles = sorted(m.profiles, key=lambda p: PROFILE_ORDER.index(p["code"]) if p["code"] in PROFILE_ORDER else 99)

    # ------------------------------------------------------------ profiles
    for p in profiles:
        root = root4
        rows = []

        def walk(nodes, depth, trail):
            for n in nodes:
                pad = f'style="padding-left:{8 + depth * 18}px"'
                if n["kind"] == "group":
                    rows.append(f'<tr class="grp"><td {pad}><strong>{esc(n["name"])}</strong> <span class="mini">group</span></td>'
                                f'<td>{st.usage_html(n, [])}</td><td>{st.card_html(n)}</td><td></td><td></td></tr>')
                    walk(n["children"], depth + 1, trail + [n["name"]])
                    continue
                seg = m.segments[n["ref"]]
                desc = seg.get("description") or ""
                slices = [s for s in m.slicings if s["profile"] == p["code"] and s["default_flavor"] == n["ref"]]
                rows.append(f'<tr><td {pad}><a href="{st.segment_href(seg["name"], root)}"><code>{esc(seg["name"])}</code></a></td>'
                            f'<td>{st.usage_html(n, [])}</td><td>{st.card_html(n)}</td>'
                            f'<td><a href="{st.flavor_href(n["ref"], root)}"><code>{esc(st.flavor_title(n["ref"]))}</code></a></td><td>{esc(desc)}</td></tr>')
                for s in slices:
                    for sl in s["slices"]:
                        rows.append(f'<tr class="slice"><td style="padding-left:{26 + depth * 18}px" class="mini">slice</td><td></td><td></td>'
                                    f'<td><a href="{st.flavor_href(sl["flavor"], root)}"><code>{esc(sl["flavor"])}</code></a></td>'
                                    f'<td class="mini">{esc(sl["when"])}</td></tr>')

        walk(p["children"], 0, [])
        group_cons = []

        def gwalk(nodes, trail):
            for n in nodes:
                if n["kind"] == "group":
                    for c in n["constraints"]:
                        group_cons.append({**c, "description": f"[{'.'.join(trail + [n['name']])}] " + c["description"]})
                    gwalk(n["children"], trail + [n["name"]])
        gwalk(p["children"], [])
        has_cocon = any(t["profile"] == p["code"] for t in m.coconstraints)
        body = f"""<article class="page model-page">{crumbs(root, ("Message profiles", f"{root}structure/index.html#profiles"))}
<p class="eyebrow">Message profile</p>
<h1><span class="num">{esc(p['code'])}</span> {esc(p['title'])}</h1>
<!--findings-->
<dl class="facts"><dt>Message type</dt><dd><code>{esc(p['message_type'])}^{esc(p['event'] or '')}^{esc(p['structure'])}</code></dd>
<dt>Description</dt><dd>{esc(p.get('description') or '')}</dd>
<dt>IGAMT ID</dt><dd><code>{esc(p['igamt_id'])}</code></dd></dl>
{f'<p><a class="button secondary" href="{st.cocon_href(p["code"], root)}">OBX co-constraint table for {esc(p["code"])}</a></p>' if has_cocon else ''}
<section><h2>Segments</h2><div class="table-wrap"><table class="model tree-table"><thead><tr><th>Segment or group</th><th>Usage</th>
<th>Cardinality</th><th>Flavor</th><th>Description or slice condition</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
{st.constraints_html(p['constraints'], 'Message-level conformance statements')}
{st.constraints_html(group_cons, 'Group-level conformance statements')}
{cards_list(profile_cards.get(p['code'], []), root)}
</article>"""
        page(f"structure/profiles/{p['code'].lower()}", f"{p['code']} {p['title']}", body, root, model_findings.get(("profile", p["code"])))

    # ------------------------------------------------------------ segments (overview per segment name) and flavors
    names = sorted({s["name"] for s in m.segments.values()})
    seg_nav = []
    for name in names:
        flavors = sorted((s for s in m.segments.values() if s["name"] == name), key=lambda s: s["label"])
        used = [s for s in flavors if s["label"] in st.used_flavors]
        shown = used or flavors
        root = root4
        nfields = max(len(s["fields"]) for s in shown)
        head = "".join(f'<th><a href="{st.flavor_href(s["label"], root)}"><code>{esc(st.flavor_title(s["label"]))}</code></a><div class="mini">'
                       + esc(", ".join(sorted({pl["profile"] for pl in st.placements_by_flavor[s["label"]] if not pl["excluded"]}, key=lambda c: PROFILE_ORDER.index(c) if c in PROFILE_ORDER else 99)))
                       + "</div></th>" for s in shown)
        rows = []
        for pos in range(1, nfields + 1):
            fname = next((s["fields"][pos - 1]["name"] for s in shown if pos <= len(s["fields"])), "")
            cells = []
            for s in shown:
                if pos > len(s["fields"]):
                    cells.append("<td></td>")
                    continue
                f = s["fields"][pos - 1]
                preds = [x for x in s["predicates"] if (x.get("target_path") or "").startswith(f"{pos}[")]
                cells.append(f'<td>{st.usage_html(f, preds)} <span class="mini">{st.card_html(f)}</span></td>')
            mentions = field_cards.get((name, pos), [])
            note = f' <span class="mini" title="Discussed in {len(mentions)} section(s)">●</span>' if mentions else ""
            rows.append(f'<tr id="f{pos}"><th scope="row"><code>{esc(name)}-{pos}</code>{note}</th><td>{esc(fname)}</td>{"".join(cells)}</tr>')
        disc = []
        for pos in range(1, nfields + 1):
            cids = field_cards.get((name, pos), [])
            if cids:
                links = ", ".join(f'<a href="{root}{c}/index.html">{esc(by_id[c].number)} {esc(by_id[c].title)}</a>' for c in dict.fromkeys(cids) if c in by_id)
                disc.append(f'<li><a href="#f{pos}"><code>{esc(name)}-{pos}</code></a>: {links}</li>')
        unused = [s for s in flavors if s["label"] not in st.used_flavors]
        desc = flavors[0].get("description") or ""
        body = f"""<article class="page model-page">{crumbs(root, ("Segments", f"{root}structure/index.html#segments"))}
<p class="eyebrow">Segment</p><h1><span class="num">{esc(name)}</span> {esc(desc)}</h1>
<p>Usage and cardinality of every {esc(name)} field in each flavor used by the message profiles. Hover over a usage to see what it means
or, for conditional usage, its condition. Open a flavor for data types, lengths, value sets, and conformance statements.</p>
<div class="table-wrap"><table class="model seg-matrix"><thead><tr><th>Field</th><th>Name</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{f'<section class="related"><h2>Fields discussed in the guide</h2><ul>{"".join(disc)}</ul></section>' if disc else ''}
{f'<p class="mini">Also defined in the export but not used by any message: {", ".join(esc(s["label"]) for s in unused)}.</p>' if unused and used else ''}
</article>"""
        page(f"structure/segments/{slug(name)}", f"{name} segment", body, root)
        seg_nav.append({"i": f"structure-seg-{slug(name)}", "t": f"{name} {desc}", "n": "", "p": f"structure/segments/{slug(name)}/index.html", "f": [0, 0, 0]})

        for s in flavors:
            root = "../" * 4  # structure/segments/<name>/<flavor>/index.html
            rows = []
            for f in s["fields"]:
                pos = f["position"]
                preds = [x for x in s["predicates"] if (x.get("target_path") or "").startswith(f"{pos}[")]
                rows.append(f'<tr id="f{pos}"><th scope="row"><code>{esc(name)}-{pos}</code></th><td>{esc(f["name"])}</td>'
                            f'<td>{st.dt_link(f["datatype"], root)}</td><td>{st.usage_html(f, preds)}</td><td>{st.card_html(f)}</td>'
                            f'<td>{st.length_html(f)}</td><td>{st.bindings_html(f, root)}</td></tr>')
            pls = st.placements_by_flavor.get(s["label"], [])
            used_in = "".join(
                f'<li><a href="{st.profile_href(pl["profile"], root)}">{esc(pl["profile"])}</a> <code>{esc(pl["path"])}</code>'
                + (f' <span class="mini">— slice: {esc(pl["slice"])}</span>' if pl["slice"] else "")
                + (' <span class="mini">(not supported)</span>' if pl["excluded"] else "") + "</li>" for pl in pls)
            dm = ""
            if s.get("dynamic_mapping"):
                dm = ('<p class="mini">Dynamic mapping: the data type of field ' + ", ".join(
                    f"{esc(x.get('position'))} is given by field {esc(x.get('reference'))}" for x in s["dynamic_mapping"]) + ".</p>")
            note = "" if s["label"] in st.used_flavors else '<p class="callout">This flavor is defined in the export but not used by any message profile.</p>'
            body = f"""<article class="page model-page">{crumbs(root, ("Segments", f"{root}structure/index.html#segments"), (name, st.segment_href(name, root)))}
<p class="eyebrow">Segment flavor</p><h1><code>{esc(st.flavor_title(s['label']))}</code></h1>
<!--findings-->
{note}<p>{esc(s.get('description') or '')}. HL7 version {esc(s.get('version') or '')}.</p>
<section><h2>Used in</h2><ul>{used_in or '<li class="mini">No message.</li>'}</ul></section>
<section><h2>Fields</h2><div class="table-wrap"><table class="model"><thead><tr><th>Field</th><th>Name</th><th>Data type</th><th>Usage</th>
<th>Cardinality</th><th>Length</th><th>Value sets</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>{dm}</section>
{st.predicates_html(s['predicates'], name + '-')}
{st.constraints_html(s['constraints'])}
</article>"""
            page(f"structure/segments/{slug(name)}/{st.flavor_slug(s['label'])}", st.flavor_title(s["label"]), body, root,
                 model_findings.get(("flavor", s["label"])))

    # ------------------------------------------------------------ datatypes
    dts = sorted(m.datatypes.values(), key=lambda d: (d["label"], d["xml_id"]))
    for d in dts:
        root = root4
        rows = []
        for i, c in enumerate(d["components"], 1):
            preds = [x for x in d["predicates"] if (x.get("target_path") or "").startswith(f"{i}[")]
            rows.append(f'<tr id="c{i}"><th scope="row"><code>{esc(d["name"])}.{i}</code></th><td>{esc(c["name"])}</td>'
                        f'<td>{st.dt_link(c["datatype"], root)}</td><td>{st.usage_html(c, preds)}</td><td>{st.length_html(c)}</td>'
                        f'<td>{st.bindings_html(c, root)}</td></tr>')
        used_by = []
        for u in d["used_by"]:
            if u in m.segments:
                used_by.append(f'<a href="{st.flavor_href(u, root)}"><code>{esc(st.flavor_title(u))}</code></a>')
            else:
                x = next((x for x in m.datatypes.values() if x["label"] == u), None)
                used_by.append(f'<a href="{st.dt_href(x["xml_id"], root)}"><code>{esc(u)}</code></a>' if x else f"<code>{esc(u)}</code>")
        comps = (f'<section><h2>Components</h2><div class="table-wrap"><table class="model"><thead><tr><th>Component</th><th>Name</th><th>Data type</th>'
                 f'<th>Usage</th><th>Length</th><th>Value sets</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
                 if rows else '<p>Primitive data type (no components).</p>')
        title = d["label"] + (f" (HL7 {d['version']})" if d["xml_id"] != d["label"] else "")
        body = f"""<article class="page model-page">{crumbs(root, ("Data types", f"{root}structure/index.html#datatypes"))}
<p class="eyebrow">Data type</p><h1><code>{esc(title)}</code> {esc(d.get('description') or '')}</h1>
<!--findings-->
{comps}
{st.predicates_html(d['predicates'], d['name'] + '.')}
{st.constraints_html(d['constraints'])}
{f'<section><h2>Used by</h2><p>{", ".join(used_by)}</p></section>' if used_by else ''}
</article>"""
        page(f"structure/datatypes/{slug(d['xml_id'])}", d["label"], body, root, model_findings.get(("dt", d["label"])))

    # ------------------------------------------------------------ value sets
    vss = sorted(m.value_sets.values(), key=lambda v: v["id"].lower())
    for v in vss:
        root = root4
        codes = "".join(
            f'<tr><td><code>{esc(c["code"])}</code></td><td>{esc(c.get("display") or "")}</td><td>{esc(c.get("system") or "")}</td>'
            f'<td>{st.usage_html(c, []) if c.get("usage") else ""}</td><td class="mini">{esc(c.get("comments") or "")}</td></tr>'
            for c in v["codes"])
        bound = "".join(f'<li><a href="{root}{esc(href)}">{esc(label)}</a></li>' for label, href in st.bound_at.get(v["id"], []))
        ext = v.get("external") or {}
        body = f"""<article class="page model-page">{crumbs(root, ("Value sets", f"{root}structure/index.html#value-sets"))}
<p class="eyebrow">Value set</p><h1><code>{esc(v['id'])}</code> {esc(v.get('name') or '')}</h1>
<!--findings-->
<dl class="facts"><dt>Description</dt><dd>{esc(v.get('description') or '')}</dd>
<dt>Stability / extensibility</dt><dd>{esc(v.get('stability') or '')} / {esc(v.get('extensibility') or '')}</dd>
<dt>Content</dt><dd>{esc(v.get('content_definition') or '')}{', excluded from validation' if v.get('no_validation') else ''}</dd>
{f"<dt>External source</dt><dd>{esc(', '.join(f'{k}: {x}' for k, x in ext.items()))}</dd>" if ext else ''}
<dt>Codes</dt><dd>{len(v['codes'])}</dd></dl>
{f'<section><h2>Bound to</h2><ul class="cols">{bound}</ul></section>' if bound else '<p class="mini">Not bound to any element.</p>'}
{f'<section><h2>Codes</h2><div class="table-wrap"><table class="model"><thead><tr><th>Code</th><th>Display name</th><th>Code system</th><th>Usage</th><th>Comments</th></tr></thead><tbody>{codes}</tbody></table></div></section>' if codes else ''}
</article>"""
        page(f"structure/value-sets/{slug(v['id'])}", v["id"], body, root, model_findings.get(("vs", v["id"])))

    # ------------------------------------------------------------ co-constraints
    for code in [p["code"] for p in profiles]:
        tables = [t for t in m.coconstraints if t["profile"] == code]
        if not tables:
            continue
        root = root4
        parts = []
        n = 0
        for t in tables:
            for tab in t["tables"]:
                n += 1
                cond = tab.get("condition") or "Always (applies to every group)"

                def row_html(r, group=None):
                    loinc = next((w.get("code") for w in r["when"] if w.get("code")), "")
                    obx2 = ", ".join(th.get("value", "") for th in r["then"] if th["field"] == "OBX-2" and th.get("value"))
                    obx5 = "<br>".join(", ".join(st.vs_link(x, root) for x in th.get("value_sets", [])) + (f' <span class="mini">({esc(th["strength"])})</span>' if th.get("strength") else "")
                                       for th in r["then"] if th["field"] == "OBX-5")
                    prim = ' <span class="mini">first in group</span>' if r.get("primary") else ""
                    return (f'<tr><td>{esc(group or "")}</td><td><code>{esc(loinc)}</code>{prim}</td><td>{st.usage_html({"usage": r["usage"]}, [])}</td>'
                            f'<td>[{esc(r["min"])}..{esc(r["max"])}]</td><td><code>{esc(obx2)}</code></td><td>{obx5}</td></tr>')
                rows = [row_html(r) for r in tab["rows"]]
                for g in tab.get("groups", []):
                    rows.append(f'<tr class="grp"><td colspan="6"><strong>{esc(g["name"])}</strong> · {st.usage_html({"usage": g["usage"]}, [])} '
                                f'[{esc(g["min"])}..{esc(g["max"])}]</td></tr>')
                    rows += [row_html(r, "↳") for r in g["rows"]]
                gb = f' Grouped by {esc(", ".join(tab["group_by"]))}.' if tab.get("group_by") else ""
                parts.append(f'<section id="table-{n}"><h2>Table {n}</h2><p><strong>When:</strong> {esc(cond)}.{gb}</p>'
                             f'<div class="table-wrap"><table class="model"><thead><tr><th>Group</th><th>OBX-3 (LOINC)</th><th>Usage</th>'
                             f'<th>Cardinality</th><th>OBX-2</th><th>OBX-5 value set</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')
        loc = ", ".join(f"<code>{esc(t['location'])}</code>" for t in tables)
        body = f"""<article class="page model-page">{crumbs(root, ("Co-constraints", f"{root}structure/index.html#coconstraints"))}
<p class="eyebrow">OBX co-constraints</p><h1><span class="num">{esc(code)}</span> OBX co-constraint tables</h1>
<!--findings-->
<p>Which observations (OBX-3) may appear in each kind of Order Segment Group in <a href="{st.profile_href(code, root)}">{esc(code)}</a>,
with their value type (OBX-2) and value set (OBX-5). Applies at {loc}. A table applies when its condition on the group's RXA holds.</p>
{''.join(parts)}
</article>"""
        page(f"structure/coconstraints/{code.lower()}", f"{code} co-constraints", body, root, model_findings.get(("cocon", code)))

    # ------------------------------------------------------------ chapter index
    root = root2
    src = (m.dir / "source.yml").read_text(encoding="utf-8") if (m.dir / "source.yml").exists() else ""
    export = re.search(r"^export: (.*)$", src, re.M)
    prof_lis = "".join(f'<li><a href="{st.profile_href(p["code"], root)}"><span class="num">{esc(p["code"])}</span> {esc(p["title"])}</a> '
                       f'<span class="mini"><code>{esc(p["message_type"])}^{esc(p["event"] or "")}</code></span></li>' for p in profiles)
    seg_lis = "".join(
        f'<li><a href="{st.segment_href(n, root)}"><code>{esc(n)}</code> {esc(next(s for s in m.segments.values() if s["name"] == n).get("description") or "")}</a> '
        f'<span class="mini">{len([s for s in m.segments.values() if s["name"] == n and s["label"] in st.used_flavors])} flavor(s)</span></li>' for n in names)
    constrained = [d for d in dts if d["xml_id"] != d["name"] or d["constraints"] or d["predicates"]]
    base = [d for d in dts if d not in constrained]
    dt_lis = lambda ds: "".join(f'<li><a href="{st.dt_href(d["xml_id"], root)}"><code>{esc(d["label"])}</code></a> <span class="mini">{esc(d.get("description") or "")}</span></li>' for d in ds)  # noqa: E731
    bound_vs = [v for v in vss if v["id"] in st.bound_at]
    vs_rows = "".join(
        f'<tr><td><a href="{st.vs_href(v["id"], root)}"><code>{esc(v["id"])}</code></a></td><td>{esc(v.get("name") or "")}</td>'
        f'<td class="n">{len(v["codes"])}</td><td>{esc(v.get("stability") or "")}/{esc(v.get("extensibility") or "")}</td></tr>' for v in vss)
    cocon_lis = "".join(f'<li><a href="{st.cocon_href(p["code"], root)}">{esc(p["code"])} {esc(p["title"])}</a></li>'
                        for p in profiles if any(t["profile"] == p["code"] for t in m.coconstraints))
    gen_panel = findings_panel(general_findings, root, {}) if general_findings else ""
    body = f"""<article class="page model-page">
<nav class="crumbs" aria-label="Breadcrumb"><a href="{root}index.html">Home</a></nav>
<h1><span class="num">7</span> Message Infrastructure</h1>
<p>This chapter is generated from the IGAMT conformance export{f' (<code>{esc(export.group(1))}</code>)' if export else ''}. IGAMT is the
authoritative source for message structure: corrections are made there and appear here with the next export. Sections of the guide that
mention a field, profile, or value set link to these pages, and each segment page lists the sections that discuss its fields.
The <a href="{root}quality/igamt/index.html">narrative and IGAMT comparison</a> lists where the two disagree.</p>
{gen_panel}
<nav class="page-toc" aria-label="On this page"><ol><li><a href="#profiles">Message profiles ({len(profiles)})</a></li>
<li><a href="#segments">Segments ({len(names)})</a></li><li><a href="#coconstraints">OBX co-constraints</a></li>
<li><a href="#datatypes">Data types ({len(dts)})</a></li><li><a href="#value-sets">Value sets ({len(vss)})</a></li></ol></nav>
<section id="profiles"><h2>Message profiles</h2><ul class="model-list">{prof_lis}</ul></section>
<section id="segments"><h2>Segments</h2><ul class="model-list cols">{seg_lis}</ul></section>
<section id="coconstraints"><h2>OBX co-constraints</h2><ul class="model-list">{cocon_lis}</ul></section>
<section id="datatypes"><h2>Data types</h2><h3>Flavors constrained for this guide</h3><ul class="model-list cols">{dt_lis(constrained)}</ul>
<details><summary>Base HL7 data types ({len(base)})</summary><ul class="model-list cols">{dt_lis(base)}</ul></details></section>
<section id="value-sets"><h2>Value sets</h2><p class="mini">{len(bound_vs)} of {len(vss)} are bound to an element.</p>
<div class="table-wrap"><table class="model"><thead><tr><th>ID</th><th>Name</th><th>Codes</th><th>Stability/extensibility</th></tr></thead>
<tbody>{vs_rows}</tbody></table></div></section>
</article>"""
    page("structure", "7 Message Infrastructure", body, root)

    nav = [{"i": f"structure-{p['code'].lower()}", "t": p["title"], "n": p["code"], "p": f"structure/profiles/{p['code'].lower()}/index.html",
            "f": _counts(model_findings.get(("profile", p["code"]), []))} for p in profiles]
    nav.append({"i": "structure-segments", "t": "Segments", "n": "", "p": "structure/index.html#segments", "f": [0, 0, 0], "c": seg_nav})
    nav.append({"i": "structure-cocon", "t": "OBX co-constraints", "n": "", "p": "structure/index.html#coconstraints", "f": [0, 0, 0],
                "c": [{"i": f"structure-cocon-{p['code'].lower()}", "t": f"{p['code']} co-constraints", "n": "",
                       "p": f"structure/coconstraints/{p['code'].lower()}/index.html", "f": _counts(model_findings.get(("cocon", p["code"]), []))}
                      for p in profiles if any(t["profile"] == p["code"] for t in m.coconstraints)]})
    nav.append({"i": "structure-datatypes", "t": "Data types", "n": "", "p": "structure/index.html#datatypes", "f": [0, 0, 0]})
    nav.append({"i": "structure-value-sets", "t": "Value sets", "n": "", "p": "structure/index.html#value-sets", "f": [0, 0, 0]})
    return nav, st


def _counts(items):
    return [sum(f["severity"] == s for f in items) for s in ("issue", "warning", "note")]


def _finding_page(st: Structure, loc: str):
    """Map a model:… finding location to the page that shows it."""
    m = st.m
    if loc.startswith("vs:"):
        return ("vs", loc[3:])
    if loc.startswith("dt:"):
        return ("dt", loc[3:])
    if loc.startswith("cocon:"):
        return ("cocon", loc.split(":")[1])
    mm = re.match(r"^(.+)-(\d+)$", loc)
    if mm and mm.group(1) in m.segments:
        return ("flavor", mm.group(1))
    mm = re.match(r"^(.+)\.(\d+)$", loc)
    if mm:
        return ("dt", mm.group(1))
    return None
