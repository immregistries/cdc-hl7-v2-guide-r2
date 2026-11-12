#!/usr/bin/env python3
"""Quality checks on the card tree.

    python tools/check_cards.py

Reads only committed content (cards/, data/, quality/), so it runs anywhere.
Writes output/quality/findings.json and output/quality/report.md, and (when model/
exists) output/quality/igamt.json with the narrative/IGAMT comparison data.

Every finding has a stable ID derived from its rule and location, so decisions
recorded in quality/dispositions.yml stay attached across builds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guidecards import (  # noqa: E402
    CARDS_DIR, DATA_DIR, META, REPO, find_verbs, load_tree, norm_title, read_yaml, subject_of, walk, write_text,
)
import compare_structure  # noqa: E402
import example_checks  # noqa: E402

QUALITY_DIR = REPO / "quality"
SEVERITIES = ("issue", "warning", "note")
CATEGORIES = {
    "structure": "Structure and editorial",
    "conformance": "Conformance language",
    "figures": "Figures and tables",
    "references": "References, glossary, and links",
    "conversion": "Conversion",
    **compare_structure.CATEGORIES,
    **example_checks.CATEGORY,
}
EXAMPLES_DIR = REPO / "examples"
MODEL_DIR = REPO / "model"
MUST_RE = re.compile(r"\b(must not|must|required to|is required|are required)\b", re.I)
CITATION_RE = re.compile(r"\[(\d{1,2})\]")


class Findings:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, rule, category, severity, message, card=None, location=None, key=None, evidence=None):
        basis = "|".join(str(x) for x in (rule, card or "", location or "", key or ""))
        fid = f"qf-{rule}-{hashlib.sha1(basis.encode('utf-8')).hexdigest()[:8]}"
        item = {"id": fid, "rule": rule, "category": category, "severity": severity,
                "card": card, "location": location, "message": message}
        if evidence:
            item["evidence"] = evidence
        self.items.append(item)


def words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def strip_md(text: str) -> str:
    return re.sub(r"[*_`\\]", "", re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text))


def snippet(text: str, n: int = 140) -> str:
    text = " ".join(strip_md(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def see_targets(text: str) -> list[str]:
    """Pointers such as 'See Key Terms.' or 'See A and B; see also C for …'."""
    text = re.sub(r"\bvs\.", "vs", text)
    targets = []
    for m in re.finditer(r"\b[Ss]ee (?:also )?(.+?)(?:\.(?:\s|$)|$)", text):
        for part in re.split(r";\s*(?:[Ss]ee (?:also )?)?", m.group(1)):
            part = re.split(r"\s+for\s+(?:how|the|a|an|more|details)\b", part)[0]
            if part.strip():
                targets.append(part.strip())
    return targets


def unresolved_part(target: str, titles: list[str]) -> str:
    """Remove every known section title (and appendix names) from the target;
    return what is left if it still looks like a name."""
    rest = target
    for title in titles:
        title = re.sub(r"\bvs\.", "vs", title)
        pattern = re.escape(title).replace(r"\ ", r"\s+").replace("&", "(?:&|and)")
        rest = re.sub(pattern, " ", rest, flags=re.I)
    rest = re.sub(r"\bAppendix\s+[A-Z]\b", " ", rest)
    rest = re.sub(r"\b(and|or|the|in|section|sections|both|also|see)\b|[,;()]", " ", rest, flags=re.I)
    rest = " ".join(rest.split())
    return rest if re.search(r"[A-Z]", rest) else ""


def run_checks(cards_dir: Path, data_dir: Path, quality_dir: Path, model_dir: Path | None = MODEL_DIR) -> tuple[list, list[dict]]:
    roots, items, _ = run_checks_full(cards_dir, data_dir, quality_dir, model_dir)
    return roots, items


def run_checks_full(cards_dir: Path, data_dir: Path, quality_dir: Path, model_dir: Path | None = MODEL_DIR):
    """Like run_checks, and also returns the narrative/IGAMT comparison data (None without model/)."""
    config = read_yaml(quality_dir / "config.yml", {}) or {}
    roots = load_tree(cards_dir)
    cards = list(walk(roots))
    f = Findings()
    exempt = set(config.get("prose_verbs_exempt", []))
    max_par = config.get("max_paragraphs", 3)
    max_words = config.get("max_words", 350)
    max_st_words = config.get("max_statement_words", 60)

    # ---------------------------------------------------------------- structure
    titles = defaultdict(list)
    for c in cards:
        titles[norm_title(c.title)].append(c)
        has_content = c.narrative.strip() or c.statements or c.meta.get("figures") or c.meta.get("tables") or c.meta.get("glossary")
        if not has_content:
            if c.children:
                f.add("no-introduction", "structure", "note",
                      "This section has no introductory text of its own; it only lists its sub-sections. A sentence or two of orientation would help readers.",
                      card=c.id)
            else:
                f.add("empty-card", "structure", "issue", "This card has no content in the draft.", card=c.id)
        if c.meta.get("glossary"):
            continue
        pars = c.paragraphs
        n_words = words(strip_md(c.narrative))
        many_blocks = len(pars) > config.get("warn_paragraphs", 6) and n_words > config.get("min_words_for_blocks", 200)
        if n_words > max_words or many_blocks:
            very = n_words > config.get("warn_words", 500)
            f.add("long-card", "structure", "warning" if very else "note",
                  f"Narrative is {len(pars)} blocks and {n_words} words (target: up to {max_par} paragraphs). Consider splitting into child cards or tightening the text.",
                  card=c.id, evidence={"blocks": len(pars), "words": n_words})
    for key, same in titles.items():
        if len(same) > 1:
            for c in same:
                others = ", ".join(f"{o.number} {o.title}" for o in same if o is not c)
                f.add("duplicate-title", "structure", "note",
                      f"Another card has the same title ({others}). Distinct titles make navigation and links clearer.",
                      card=c.id)

    # ---------------------------------------------------------------- conformance language
    actors = Counter()
    for c in cards:
        seen_par = Counter()
        for p in c.paragraphs + [s["text"] for s in c.statements]:
            seen_par[" ".join(p.split())] += 1
        for p, n in seen_par.items():
            if n > 1:
                f.add("repeated-text", "structure", "warning",
                      f"The same text appears {n} times on this card.", card=c.id, key=p[:120],
                      evidence={"text": snippet(p, 300)})
        occurrence = Counter()
        if c.id not in exempt:
            for p in c.paragraphs:
                occurrence[p] += 1
                key = p[:120] + (f"#{occurrence[p]}" if occurrence[p] > 1 else "")
                verbs = find_verbs(p)
                if verbs:
                    f.add("verb-in-prose", "conformance", "warning",
                          f"Narrative uses the conformance verb{'s' if len(set(verbs)) > 1 else ''} {', '.join(dict.fromkeys(verbs))}. "
                          "Move the requirement to a conformance statement, or use lowercase wording if it is not a requirement.",
                          card=c.id, key=key, evidence={"text": snippet(p, 300)})
                elif MUST_RE.search(p):
                    f.add("normative-prose", "conformance", "note",
                          f"Narrative uses \"{MUST_RE.search(p).group(1)}\", which reads as a requirement. "
                          "If it is one, state it as a conformance statement; otherwise consider softer wording.",
                          card=c.id, key=key, evidence={"text": snippet(p, 300)})
        for s in c.statements:
            actors[s.get("actor") or ""] += 1
            if s.get("verbs"):
                f.add("multi-verb-statement", "conformance", "warning",
                      f"Statement combines {', '.join(s['verbs'])}. Each statement should carry one requirement so it can be tested and referenced on its own.",
                      card=c.id, location=s["id"], evidence={"text": s["text"]})
            elif len(find_verbs(s["text"])) > 1:
                f.add("compound-statement", "conformance", "note",
                      "Statement repeats its conformance verb, so it may hold more than one requirement. Consider splitting it.",
                      card=c.id, location=s["id"], evidence={"text": s["text"]})
            if not s.get("actor"):
                subject = subject_of(s["text"])
                why = (f"Its subject is \"{subject}\", not a system or party" if subject
                       else "It does not open with the system or party it applies to")
                f.add("no-actor", "conformance", "note",
                      f"{why}, so it is unclear who must comply. Naming the responsible party (for example, \"Submitting systems SHALL …\" or \"IIS SHALL …\") makes the requirement testable.",
                      card=c.id, location=s["id"], evidence={"text": s["text"]})
            if words(s["text"]) > max_st_words:
                f.add("long-statement", "conformance", "note",
                      f"Statement is {words(s['text'])} words. Long statements are hard to test and cite.",
                      card=c.id, location=s["id"], evidence={"text": s["text"]})
    named = {a: n for a, n in actors.items() if a}
    if len(named) > 1:
        f.add("actor-vocabulary", "conformance", "note",
              "Statements name their actors in several ways. A small, consistent set of actor names (defined in Key Terms) makes requirements easier to apply and test.",
              key="document", evidence={"actors": dict(sorted(named.items(), key=lambda kv: -kv[1]))})

    # ---------------------------------------------------------------- figures
    numbers = []
    for c in cards:
        for fig in c.meta.get("figures", []):
            numbers.append((fig.get("number"), c))
            f.add("image-figure", "figures", "note",
                  "This figure is an image. If it holds a table or text, convert it to a structured table so it can be searched, read by screen readers, and commented on; diagrams can become Mermaid. "
                  + ("It also needs alternative text." if not fig.get("alt") else ""),
                  card=c.id, location=fig["id"], evidence={"caption": fig.get("caption", "")})
            if fig.get("number") is None:
                f.add("uncaptioned-figure", "figures", "warning", "Figure has no numbered caption.", card=c.id, location=fig["id"])
        for t in c.meta.get("tables", []):
            if t.get("number") is not None:
                numbers.append((t.get("number"), c))
    ints = [int(re.match(r"\d+", str(n)).group()) for n, _ in numbers if n is not None]
    if ints:
        missing = sorted(set(range(1, max(ints) + 1)) - set(ints))
        dupes = sorted(n for n, k in Counter(str(n) for n, _ in numbers if n is not None).items() if k > 1)
        out_of_order = any(b < a for a, b in zip(ints, ints[1:]))
        if missing or dupes or out_of_order:
            parts = []
            if missing:
                parts.append(f"missing numbers {', '.join(map(str, missing))}")
            if dupes:
                parts.append(f"repeated numbers {', '.join(dupes)}")
            if out_of_order:
                parts.append("numbers out of order")
            lettered = sorted({str(n) for n, _ in numbers if n is not None and not str(n).isdigit()})
            if lettered:
                parts.append(f"lettered sub-figures {', '.join(lettered)}")
            f.add("figure-numbering", "figures", "note",
                  "Figure numbering has gaps or irregularities: " + "; ".join(parts) + ". On the web, figures are identified by card, so numbers matter mainly for the printed document.",
                  key="document")

    # ---------------------------------------------------------------- references and glossary
    refs = (read_yaml(data_dir / "references.yml", {}) or {}).get("references", [])
    ref_numbers = {r["number"] for r in refs}
    cited = set()
    for c in cards:
        for text in [c.narrative] + [s["text"] for s in c.statements]:
            for n in CITATION_RE.findall(text):
                cited.add(int(n))
                if int(n) not in ref_numbers:
                    f.add("unknown-citation", "references", "issue",
                          f"Citation [{n}] does not match any entry in the resources appendix.", card=c.id, key=n)
    for r in refs:
        if r["number"] not in cited and not r.get("group"):
            f.add("uncited-reference", "references", "note",
                  f"Resource {r['number']} ({r['title']}) is listed as cited but is not cited in the narrative.",
                  location=f"ref-{r['number']}")
        if not r.get("url"):
            f.add("reference-without-url", "references", "warning",
                  f"Resource {r['number']} ({r['title']}) has no link.", location=f"ref-{r['number']}")

    title_list = sorted({c.title for c in cards}, key=len, reverse=True)
    glossary = read_yaml(data_dir / "glossary.yml", {}) or {}
    for group in glossary.get("groups", []):
        for entry in group.get("entries", []):
            for target in see_targets(strip_md(entry["definition"])):
                leftover = unresolved_part(target, title_list)
                if leftover:
                    f.add("glossary-see-unresolved", "references", "warning",
                          f"Glossary entry \"{entry['term']}\" points to \"{target}\"; \"{leftover}\" does not match a section title, so it cannot become a link.",
                          location=f"glossary:{entry['term']}", key=target)

    history = (read_yaml(data_dir / "change-history.yml", {}) or {}).get("changes", None)
    if history is not None and not history:
        f.add("empty-change-history", "structure", "note", "The Change History table is empty.", key="document")

    # ---------------------------------------------------------------- conversion notes
    notes = read_yaml(cards_dir / META / "conversion-notes.yml", {}) or {}
    variants = Counter()
    for card_id, card_notes in (notes.get("cards") or {}).items():
        for note in card_notes:
            if note.startswith("context-heading: "):
                variants[note.split(": ", 1)[1].strip()] += 1
            elif note.startswith("Narrative text follows"):
                f.add("statements-mid-section", "structure", "note",
                      "In the draft, explanatory text continues after the conformance statements. Cards show statements after the narrative, so check that the order still reads well.",
                      card=card_id)
            elif note.startswith("promoted-statements: "):
                ids = note.split(": ", 1)[1].split(", ")
                f.add("statement-from-paragraph", "conformance", "note",
                      f"{len(ids)} requirement{'s were' if len(ids) > 1 else ' was'} written as {'paragraphs' if len(ids) > 1 else 'a paragraph'} in the draft and {'are' if len(ids) > 1 else 'is'} shown here as conformance statement{'s' if len(ids) > 1 else ''} (wording unchanged): "
                      + ", ".join(i.rsplit("--", 1)[1] for i in ids) + ".",
                      card=card_id, evidence={"statements": ids})
            elif note.startswith("Internal Word cross-reference"):
                f.add("internal-xref", "references", "note",
                      "A Word cross-reference became plain text; it should become a managed link to the target section.",
                      card=card_id, key=note)
    if len(variants) > 1:
        f.add("heading-variants", "structure", "note",
              "The opening sub-heading is spelled several ways: " + "; ".join(f"\"{k}\" ({v})" for k, v in variants.most_common()) + ". (On the web this text becomes the section's own introduction.)",
              key="document")

    # ---------------------------------------------------------------- narrative vs IGAMT structure
    structure = compare_structure.run(cards, model_dir, quality_dir, f, config) if model_dir else None
    examples = example_checks.run(cards, cards_dir.parent / "examples", model_dir, f, config) if model_dir else None
    if structure is not None and examples is not None:
        structure["examples"] = examples

    # ---------------------------------------------------------------- manual
    for m in read_yaml(quality_dir / "manual-findings.yml", []) or []:
        item = {"id": m["id"], "rule": "manual", "category": m.get("category", "structure"),
                "severity": m.get("severity", "note"), "card": m.get("card"),
                "location": m.get("location"), "message": m["message"]}
        f.items.append(item)

    # ---------------------------------------------------------------- dispositions
    dispositions = read_yaml(quality_dir / "dispositions.yml", {}) or {}
    for item in f.items:
        if item["id"] in dispositions:
            item["disposition"] = dispositions[item["id"]]
    seen = Counter(i["id"] for i in f.items)
    if any(v > 1 for v in seen.values()):
        raise SystemExit(f"Duplicate finding IDs: {[k for k, v in seen.items() if v > 1]}")
    return roots, f.items, structure


def write_report(roots, findings: list[dict], path: Path) -> None:
    cards = {c.id: c for c in walk(roots)}
    by_sev = Counter(i["severity"] for i in findings)
    by_rule = Counter(i["rule"] for i in findings)
    lines = [
        "# Quality findings", "",
        f"{len(findings)} findings: " + ", ".join(f"{by_sev[s]} {s}{'s' if by_sev[s] != 1 else ''}" for s in SEVERITIES),
        "", "| Rule | Category | Count |", "|---|---|---:|",
    ]
    rule_cat = {i["rule"]: i["category"] for i in findings}
    for rule, n in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{rule}` | {CATEGORIES.get(rule_cat[rule], rule_cat[rule])} | {n} |")
    for cat, label in CATEGORIES.items():
        items = [i for i in findings if i["category"] == cat]
        if not items:
            continue
        lines += ["", f"## {label}", ""]
        items.sort(key=lambda i: (SEVERITIES.index(i["severity"]), cards[i["card"]].number.split(".") if i.get("card") in cards else [], i["id"]))
        for i in items:
            where = ""
            if i.get("card") in cards:
                c = cards[i["card"]]
                rel = c.path.relative_to(REPO).as_posix()
                where = f" — [{c.number} {c.title}](../../{rel}/)"
            if i.get("location"):
                where += f" `{i['location']}`"
            lines.append(f"- **{i['severity']}** `{i['id']}`{where}: {i['message']}")
            ev = i.get("evidence") or {}
            if "text" in ev:
                lines.append(f"  > {ev['text']}")
            elif "xml" in ev and isinstance(ev["xml"], str):
                lines.append(f"  > XML: {ev['xml']}")
            elif "actors" in ev:
                lines.append("  " + "; ".join(f"{k} ({v})" for k, v in ev["actors"].items()))
    write_text(path, "\n".join(lines) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cards", type=Path, default=CARDS_DIR)
    parser.add_argument("--data", type=Path, default=DATA_DIR)
    parser.add_argument("--out", type=Path, default=REPO / "output" / "quality")
    args = parser.parse_args(argv)
    roots, findings, structure = run_checks_full(args.cards, args.data, QUALITY_DIR)
    args.out.mkdir(parents=True, exist_ok=True)
    write_text(args.out / "findings.json", json.dumps(findings, indent=2, ensure_ascii=False) + "\n")
    if structure:
        write_text(args.out / "igamt.json", json.dumps(structure, indent=1, ensure_ascii=False) + "\n")
    write_report(roots, findings, args.out / "report.md")
    sev = Counter(i["severity"] for i in findings)
    print(f"{len(findings)} findings ({', '.join(f'{sev[s]} {s}' for s in SEVERITIES)}). Report: {args.out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
