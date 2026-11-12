# CDC HL7 v2 Guide (Release 2): draft

> **DRAFT for review. Not for implementation.** This repository holds a working
> draft of the next HL7 Version 2.5.1 Implementation Guide for Immunization
> Messaging, a joint publication of the Centers for Disease Control and
> Prevention (CDC) and the American Immunization Registry Association (AIRA).
> Its content is under active review and will change.

**Read the draft:** <https://immregistries.github.io/cdc-hl7-v2-guide-r2/>

The guide is published as a website: a navigable tree of short, focused
sections ("cards"), followed by the message conformance profiles, segments,
data types, and value sets. Each card has a permanent link and can be commented
on. Quality findings from automated and editorial review appear alongside the
text, so reviewers can see and respond to them in context.

## How the guide is built

```text
narrative draft (Word) ──► tools/convert_narrative.py ──► cards/   ┐
IGAMT conformance export ──► tools/import_igamt.py    ──► model/      ├─► website, quality report,
example messages         ──► tools/import_examples.py ──► examples/ ┘    ballot document
```

- **Narrative.** For now, the narrative is maintained by CDC in Word and
  converted into the card tree in `cards/`. Conversion is repeatable, and card
  and statement IDs stay the same from one draft to the next. Later, the card
  tree is expected to become the source that the narrative is edited in.
- **Structure.** Message profiles, segments, data types, value sets, and
  constraints are authored in NIST/Prometheus IGAMT and imported from its
  export. IGAMT remains the authoritative source for them.
- **Source files are not in this repository.** The Word draft, the IGAMT
  export, and the example files stay with the maintainers; only the converted
  content is committed.

See [docs/architecture.md](docs/architecture.md) and the
[card format](docs/card-format.md).

## Layout

| Path | Contents |
|---|---|
| `cards/` | The narrative as a tree of cards; [`cards/INDEX.md`](cards/INDEX.md) is the table of contents |
| `examples/` | The example messages, one file per example, matched to sections; generated from CDC's list and the drafted samples |
| `model/` | The IGAMT conformance export, normalized (profiles, segments, data types, value sets, constraints, co-constraints); generated, never edited |
| `data/` | Key terms, glossary, references, and change history |
| `quality/` | Quality-check settings, reviewer findings (including the narrative/IGAMT review), and decisions on findings |
| `site/` | Theme and web assets (joint CDC/AIRA presentation) |
| `tools/` | Conversion, checks, the site builder, and (to come) the document builder |
| `tests/` | Tests for the tools |
| `docs/` | How the guide is built |

## Working with the tools

Requires Python 3.12 or later.

```powershell
pip install -r requirements.txt

# Maintainers only: convert the inputs (paths in inputs.json; see inputs.example.json)
python tools/convert_narrative.py
python tools/import_igamt.py
python tools/import_examples.py

# Anyone: run the quality checks on the committed cards
python tools/check_cards.py          # writes output/quality/report.md

# Anyone: build the website (open output/site/index.html)
python tools/build_site.py

# Tests
python -m unittest discover -s tests
```

## Status

| Part | State |
|---|---|
| Narrative cards | Converted from the 4 Nov 2026 draft: 357 cards, 595 conformance statements |
| Quality checks | Structure, conformance language, figures, references, and the narrative/IGAMT comparison ([report](https://immregistries.github.io/cdc-hl7-v2-guide-r2/main/quality/igamt/)) |
| Structured chapter (IGAMT) | Chapter 7 generated: 8 profiles, segments and flavors, data types, value sets, OBX co-constraints; linked from the narrative |
| Website | Published from `main` on every push |
| Card comments (InteropHub) | Open on topic 52 ([how it works](docs/comments.md)) |
| Example messages | 81 examples on 60+ sections, assembled into whole messages and checked against the IGAMT profiles ([Appendix A](https://immregistries.github.io/cdc-hl7-v2-guide-r2/main/examples/)) |
| Ballot document (Word/PDF) | Planned |

## License

Tools and code are licensed under the [Apache License 2.0](LICENSE). The guide
content is a draft of a CDC/AIRA publication; terms for its reuse will be
stated with the published guide.
