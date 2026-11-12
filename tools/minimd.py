"""A small Markdown renderer for the subset used in cards.

Supports paragraphs, nested bullet and numbered lists (two-space indents),
**bold**, *italic*, ***both***, [links](url), backslash escapes, and <br> in
table cells. Anything else is shown as text. Deterministic, no dependencies.
"""

from __future__ import annotations

import html
import re

_ESC = "\u0000"
_PUNCT = r"\\`*_{}\[\]()#+\-.!<>|~"


def inline(text: str, citation_href: str | None = None) -> str:
    stash: list[str] = []

    def keep(s: str) -> str:
        stash.append(s)
        return f"{_ESC}{len(stash) - 1}{_ESC}"

    text = re.sub(r"\\([" + _PUNCT + "])", lambda m: keep(html.escape(m.group(1))), text)
    text = re.sub(r"<br\s*/?>", lambda m: keep("<br>"), text)
    text = html.escape(text, quote=False)

    def link(m):
        label, url = m.group(1), html.unescape(m.group(2))
        if not re.match(r"^(https?://|mailto:|#|\.\.?/)", url):
            return m.group(0)
        external = url.startswith("http")
        attrs = ' rel="noopener" target="_blank"' if external else ""
        return keep(f'<a href="{html.escape(url)}"{attrs}>') + label + keep("</a>")

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    if citation_href:
        text = re.sub(r"\[(\d{1,2})\]", lambda m: f'<a class="cite" href="{citation_href}#ref-{m.group(1)}">[{m.group(1)}]</a>', text)
    return re.sub(_ESC + r"(\d+)" + _ESC, lambda m: stash[int(m.group(1))], text)


_ITEM = re.compile(r"^( *)(-|\d+\.)\s+(.*)$")


def _list(lines: list[str], cite) -> str:
    out: list[str] = []
    stack: list[tuple[int, str]] = []  # (indent, tag)
    for line in lines:
        m = _ITEM.match(line)
        if not m:  # continuation of the previous item
            out.append(" " + inline(line.strip(), cite))
            continue
        indent, marker, body = len(m.group(1)), m.group(2), m.group(3)
        tag = "ul" if marker == "-" else "ol"
        while stack and stack[-1][0] > indent:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and stack[-1][0] == indent:
            out.append("</li>")
        else:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        out.append("<li>" + inline(body, cite))
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


def render(markdown: str, citation_href: str | None = None) -> str:
    blocks = [b for b in re.split(r"\n\s*\n", markdown.strip()) if b.strip()]
    html_blocks = []
    for block in blocks:
        lines = block.splitlines()
        if _ITEM.match(lines[0]):
            html_blocks.append(_list(lines, citation_href))
        else:
            html_blocks.append("<p>" + inline(" ".join(l.strip() for l in lines), citation_href) + "</p>")
    return "\n".join(html_blocks)


def table(markdown: str) -> str:
    rows = [r for r in markdown.strip().splitlines() if r.strip().startswith("|")]
    if not rows:
        return ""

    def cells(row):
        parts = re.split(r"(?<!\\)\|", row.strip())[1:-1]
        return [inline(p.strip().replace("\\|", "|")) for p in parts]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ["<table>", "<thead><tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr></thead>", "<tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)
