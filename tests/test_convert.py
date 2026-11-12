"""Tests for the narrative converter and the quality checks.

    python -m unittest discover -s tests

The tests build small Word documents in code; they need no source files.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import docx
import yaml

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

import check_cards  # noqa: E402
import convert_narrative  # noqa: E402
from guidecards import CARDS_DIR, REPO, actor_of, load_tree, walk  # noqa: E402

OVERRIDES = {
    "context_titles": ["Context and Rationale", "Context & Rationale"],
    "no_split": ["Document Structure"],
    "glossary_sections": {"Key Terms": "key-terms"},
    "stop_at": "Message Infrastructure",
    "appendices": {"Appendix B: Glossary": "glossary"},
    "promote_prose_statements": True,
}


def bold(doc, text):
    doc.add_paragraph().add_run(text).bold = True


def make_doc(path, variant=0):
    """A small draft. Later variants simulate edits between CDC drafts."""
    d = docx.Document()
    d.add_heading("Overview", level=1)
    d.add_paragraph("This guide covers immunization messaging.")
    d.add_heading("Document Structure", level=2)
    bold(d, "1. Overview")
    d.add_paragraph("The first chapter.")
    d.add_heading("Key Terms", level=2)
    d.add_paragraph("Terms used in this guide.")
    bold(d, "Actors")
    bold(d, "Immunization Information System (IIS)")
    d.add_paragraph("A population-based system.")
    d.add_heading("Patient Identifiers", level=1)
    bold(d, "Context and Rationale")
    d.add_paragraph("Identifiers link records.")
    bold(d, "Primary Identifier for Exchange" if variant < 1 else "Primary Patient Identifier for Exchange")
    d.add_paragraph("Every system uses an identifier.")
    statements = [
        "Sending systems SHALL submit a primary exchange identifier.",
        "IIS SHOULD support MR and PI identifier types.",
    ]
    if variant >= 1:
        statements = [statements[1], statements[0].replace("submit", "always submit")]
    if variant >= 2:
        statements.append("IIS SHALL retain the identifier type.")
    for s in statements:
        d.add_paragraph(s, style="List Bullet")
    d.add_paragraph("IIS SHALL NOT recycle identifiers.")  # a one-sentence requirement written as a paragraph
    if variant < 2:
        bold(d, "Security Considerations")
        d.add_paragraph("Registry identifiers are not credentials. They SHALL NOT be trusted alone. More text.")
    bold(d, "Entity Models")
    bold(d, "Patient (Entity)")
    d.add_paragraph("The patient.")
    d.add_heading("Message Infrastructure", level=1)
    d.add_paragraph("Generated from IGAMT.")
    d.add_heading("Appendix B: Glossary", level=1)
    bold(d, "Abbreviations")
    p = d.add_paragraph()
    p.add_run("IIS").bold = True
    p.add_run(" - Immunization Information System. See Key Terms.")
    d.save(path)


class ConverterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cards = self.tmp / "cards"
        (self.cards / "_meta").mkdir(parents=True)
        overrides = dict(OVERRIDES, nest={"Entity Models": ["Patient (Entity)"]})
        (self.cards / "_meta" / "overrides.yml").write_text(yaml.safe_dump(overrides), encoding="utf-8")
        self.data = self.tmp / "data"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def convert(self, variant=0):
        path = self.tmp / f"draft{variant}.docx"
        if not path.exists():  # saving again would change the file's timestamp and hash
            make_doc(path, variant)
        convert_narrative.main(["--docx", str(path), "--cards", str(self.cards), "--data", str(self.data),
                                "--report", str(self.tmp / "report.md")])
        return {c.id: c for c in walk(load_tree(self.cards))}

    def snapshot(self):
        return {p.relative_to(self.tmp).as_posix(): p.read_bytes()
                for p in sorted(self.tmp.rglob("*")) if p.is_file() and p.suffix != ".docx" and p.name != "report.md"}

    def test_structure(self):
        cards = self.convert()
        self.assertIn("patient-identifiers", cards)
        parent = cards["patient-identifiers"]
        self.assertIn("Identifiers link records.", parent.narrative)      # context → parent narrative
        self.assertNotIn("context-and-rationale", cards)
        leaf = cards["primary-identifier-for-exchange"]
        self.assertEqual([s["verb"] for s in leaf.statements], ["SHALL", "SHOULD", "SHALL NOT"])
        self.assertEqual(leaf.statements[0]["actor"], "Sending systems")
        self.assertEqual(leaf.statements[2]["id"], "primary-identifier-for-exchange--s3")
        self.assertIn("**1. Overview**", cards["document-structure"].narrative)  # no_split
        self.assertEqual(cards["patient-entity"].parent.id, "entity-models")  # nest
        security = cards["security-considerations"]
        self.assertFalse(security.statements)  # multi-sentence prose stays narrative
        terms = yaml.safe_load((self.data / "key-terms.yml").read_text(encoding="utf-8"))
        self.assertEqual(terms["groups"][0]["name"], "Actors")
        self.assertEqual(terms["groups"][0]["terms"][0]["term"], "Immunization Information System (IIS)")
        gloss = yaml.safe_load((self.data / "glossary.yml").read_text(encoding="utf-8"))
        self.assertEqual(gloss["groups"][0]["entries"][0]["definition"], "Immunization Information System. See Key Terms.")

    def test_rerun_is_identical(self):
        self.convert()
        first = self.snapshot()
        self.convert()
        self.assertEqual(first, self.snapshot())

    def test_ids_survive_edits(self):
        before = self.convert(0)
        old_leaf = before["primary-identifier-for-exchange"]
        shall_id = old_leaf.statements[0]["id"]
        should_id = old_leaf.statements[1]["id"]
        after = self.convert(1)  # retitled card, reordered and reworded statements
        self.assertIn("primary-identifier-for-exchange", after)
        self.assertEqual(after["primary-identifier-for-exchange"].title, "Primary Patient Identifier for Exchange")
        ids = {s["text"]: s["id"] for s in after["primary-identifier-for-exchange"].statements}
        self.assertEqual(ids["IIS SHOULD support MR and PI identifier types."], should_id)
        self.assertEqual(ids["Sending systems SHALL always submit a primary exchange identifier."], shall_id)

        final = self.convert(2)  # card removed, statement added
        self.assertNotIn("security-considerations", final)
        ledger = yaml.safe_load((self.cards / "_meta" / "ids.yml").read_text(encoding="utf-8"))
        retired = [e["id"] for e in ledger["cards"] if e.get("retired")]
        self.assertEqual(retired, ["security-considerations"])
        new = [s for s in final["primary-identifier-for-exchange"].statements if "retain" in s["text"]][0]
        self.assertEqual(new["id"], "primary-identifier-for-exchange--s4")  # next unused number


class ChecksTest(unittest.TestCase):
    def test_findings_are_stable_and_unique(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            cards = tmp / "cards"
            (cards / "_meta").mkdir(parents=True)
            (cards / "_meta" / "overrides.yml").write_text(yaml.safe_dump(OVERRIDES), encoding="utf-8")
            make_doc(tmp / "d.docx")
            convert_narrative.main(["--docx", str(tmp / "d.docx"), "--cards", str(cards), "--data", str(tmp / "data"),
                                    "--report", str(tmp / "r.md")])
            _, first = check_cards.run_checks(cards, tmp / "data", tmp / "quality")
            _, second = check_cards.run_checks(cards, tmp / "data", tmp / "quality")
            self.assertEqual([i["id"] for i in first], [i["id"] for i in second])
            rules = {i["rule"] for i in first}
            self.assertIn("verb-in-prose", rules)       # the Security Considerations paragraph
            self.assertIn("empty-card", rules)          # without a nest rule, Entity Models is empty
        finally:
            shutil.rmtree(tmp)

    def test_actor(self):
        self.assertEqual(actor_of("When an RSP includes a patient, the IIS SHALL return it."), "IIS")
        self.assertEqual(actor_of("The same identifiers SHOULD be used."), "")


class ExamplesTest(unittest.TestCase):
    BASE = ("MSH|^~\\&|EHR|FAC|IIS|IISF|20261007073733-0500||VXU^V04^VXU_V04|1|P|2.5.1|||ER|AL|||||Z22^CDCPHINVS|FAC|IISF\n"
            "PID|1||X1^^^MRN^MR||Pena^Rodrigo^^^^^L||20221019|M\n"
            "ORC|RE||X1.3^CDC-AIRA\n"
            "RXA|0|1|20261007||94^MMRV^CVX|0.5|mL^milliliters^UCUM||00^Administered^NIP001||||||V7737HT||MSD^Merck^MVX|||CP|A\n"
            "RXR|C38299^SUBCUTANEOUS^NCIT|RA^RIGHT ARM^HL70163\n"
            "OBX|1|CE|64994-7^Eligibility^LN|1|V03^VFC eligible - Uninsured^HL70064||||||F")

    def test_assemble(self):
        import hl7msg
        base = hl7msg.segments(self.BASE)
        # a PID clip replaces the base PID and nothing else
        segs, clip = hl7msg.assemble(base, ["PID|1||X1^^^MRN^MR||Pena^BABY^^^^^NB||20221019|M"])
        self.assertEqual(len(segs), len(base))
        self.assertEqual([hl7msg.seg_type(s) for s in segs], ["MSH", "PID", "ORC", "RXA", "RXR", "OBX"])
        self.assertEqual(clip, [1])
        self.assertEqual(hl7msg.changed_fields(segs[1], base), [5])
        # a refusal RXA clip keeps the ORC (with ORC-3 9999) and drops the administered dose's RXR and OBX
        segs, _ = hl7msg.assemble(base, ["RXA|0|1|20261007||107^DTAP^CVX|999||||||||||||00^Parental refusal^NIP002||RE|A"])
        self.assertEqual([hl7msg.seg_type(s) for s in segs], ["MSH", "PID", "ORC", "RXA"])
        self.assertTrue(hl7msg.get(segs[2], 3).startswith("9999"))
        # segments run together on one line are split
        self.assertEqual(len(hl7msg.segments("OBX|1|CE|a|1|x||||||F OBX|2|CE|b|1|y||||||F")), 2)

    def test_checker(self):
        from structure_index import Model
        import example_checks
        model_dir = REPO / "model"
        if not Model.available(model_dir):
            self.skipTest("model/ not present")
        checker = example_checks.ExampleChecker(Model(model_dir), ["IZ-41", "IZ-42"])
        profile, problems = checker.check_message(self.BASE.replace("20221019|M", "20221019-0500|M"))
        self.assertEqual(profile, "Z22")
        text = " ".join(t for _, t in problems)
        self.assertIn("PID-7.1 '20221019-0500'", text)          # TS_NZ allows no offset
        bad = self.BASE.replace("^Pena^Rodrigo", "^^Rodrigo").replace("||Pena^Rodrigo", "||^Rodrigo")
        _, problems = checker.check_message(bad)
        self.assertTrue(any("PID-5.1" in t for _, t in problems))  # family name is required for an 'L' name


def broken_links(site: Path) -> list[str]:
    """Internal links (and #anchors on HTML pages) that do not resolve in a built site."""
    import re
    ids_cache: dict = {}

    def ids(p: Path) -> set:
        if p not in ids_cache:
            ids_cache[p] = set(re.findall(r'id="([^"]+)"', p.read_text(encoding="utf-8")))
        return ids_cache[p]

    bad = set()
    for page in site.rglob("*.html"):
        for href in re.findall(r'href="([^"]+)"', page.read_text(encoding="utf-8")):
            if href.startswith(("http:", "https:", "mailto:")):
                continue
            path, _, frag = href.partition("#")
            target = (page.parent / path).resolve() if path else page.resolve()
            if not target.exists():
                bad.add(f"{page.relative_to(site)} -> {href}")
            elif frag and target.suffix == ".html" and frag not in ids(target):
                bad.add(f"{page.relative_to(site)} -> {href}")
    return sorted(bad)[:20]


class SiteTest(unittest.TestCase):
    def test_minimd(self):
        import minimd
        self.assertEqual(minimd.render("A **b** and *c* [d](https://x.org) \\*e\\* <f> [7]", citation_href="r.html"),
                         '<p>A <strong>b</strong> and <em>c</em> <a href="https://x.org" rel="noopener" target="_blank">d</a>'
                         ' *e* &lt;f&gt; <a class="cite" href="r.html#ref-7">[7]</a></p>')
        self.assertEqual(minimd.render("- one\n  - two\n- three"),
                         "<ul><li>one<ul><li>two</li></ul></li><li>three</li></ul>")
        self.assertIn("<td>a|b</td>", minimd.table("| H |\n|---|\n| a\\|b |"))

    def test_build_site(self):
        import build_site
        out = Path(tempfile.mkdtemp())
        try:
            result = build_site.build(out)
            self.assertGreater(result["cards"], 0)
            for page in ("index.html", "contents/index.html", "quality/index.html", "glossary/index.html",
                         "resources/index.html", "assets/nav.js"):
                self.assertTrue((out / page).exists(), page)
            if (REPO / "model" / "profiles.json").exists():
                for page in ("structure/index.html", "structure/profiles/z22/index.html",
                             "structure/segments/rxa/index.html", "quality/igamt/index.html"):
                    self.assertTrue((out / page).exists(), page)
            self.assertEqual(broken_links(out), [])
        finally:
            shutil.rmtree(out)


class StructureTest(unittest.TestCase):
    """Narrative/IGAMT comparison on the committed model/ (skipped if model/ is absent)."""

    def test_comparison(self):
        import compare_structure  # noqa: F401
        from structure_index import Model
        model_dir = REPO / "model"
        if not Model.available(model_dir):
            self.skipTest("model/ not present")
        m = Model(model_dir)
        self.assertEqual(m.field_name("RXA", 20), "Completion Status")
        self.assertIn("RE", m.codes(m.bindings("RXA", 20)))
        self.assertIn("HL70200_IZ01", m.component_bindings("PID", 5, 7))
        _, items, structure = check_cards.run_checks_full(CARDS_DIR, REPO / "data", REPO / "quality", model_dir)
        _, again, _ = check_cards.run_checks_full(CARDS_DIR, REPO / "data", REPO / "quality", model_dir)
        self.assertEqual([i["id"] for i in items], [i["id"] for i in again])
        self.assertTrue(structure["xref"])
        self.assertTrue(any(i["rule"] == "igamt-review" for i in items))
        self.assertTrue(any(i["rule"] == "xml-figure-cocon" for i in items))


if __name__ == "__main__":
    unittest.main()
