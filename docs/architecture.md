# Architecture

## Goals

1. **Usable and understandable.** Implementers find, understand, and link to
   what they need. Short sections, one topic each, with stable links and
   consistent placement of requirements, figures, examples, and related
   material.
2. **Visible quality.** Automated and editorial checks run on every build, and
   their findings appear next to the content they concern.
3. **Reviewable.** Every card and structured artifact has a permanent address
   and can be commented on.
4. **One source, several outputs.** The website, the quality report, and the
   ballot document (Word/PDF) come from the same content.

## Sources and authority

| Content | Authoritative source | In this repository |
|---|---|---|
| Narrative | The CDC Word draft, until the card tree becomes the source | `cards/`, converted by `tools/convert_narrative.py` |
| Conformance structure (profiles, segments, data types, value sets, constraints, co-constraints) | IGAMT | `model/`, normalized from the IGAMT export by `tools/import_igamt.py` |
| Example messages | Example definitions | `examples/` (to come) |

Structural problems found by the checks are reported as **requested changes
for IGAMT**. They are not edited here.

## The card tree

A card is one table-of-contents entry: one to three paragraphs of narrative, an
ordered list of conformance statements, and optional figures, tables,
examples, and related links. Parent cards introduce their topic, and an
"In this section" list is generated from their children. See
[card-format.md](card-format.md).

The conversion from Word:

- Word headings and the bold sub-headings within sections become cards.
- An opening "Context and Rationale" sub-heading becomes the parent card's own
  introduction.
- Bulleted requirements become conformance statements. So do one-sentence
  paragraphs that state a requirement (a conformance verb, opening with the
  party it applies to or a condition). Each card where this happened is listed
  in the quality report.
- Figures keep their numbers and captions. Word tables become Markdown tables.
- The key terms, glossary, and references become data files.
- Rules that need human judgment (sections not to split, sub-headings that
  group others, figure text alternatives) live in
  `cards/_meta/overrides.yml`.

### Stable IDs

Card IDs are matched across drafts by:

1. the IGAMT section bookmark carried in the Word export;
2. the heading path;
3. a similar title under the same parent;
4. an unchanged, unique title anywhere (a card that moved).

A card that disappears keeps its ID in the ledger as retired, and the ID is
never reused. Statement IDs (`<card-id>--s<n>`) are matched by unchanged text,
then by the most similar text; new statements take the next unused number.

## Quality checks

`tools/check_cards.py` reads only committed content. Each finding has:

- a stable ID (rule + location);
- a category and a severity (issue, warning, note);
- a message;
- evidence.

Decisions on findings are recorded in `quality/dispositions.yml`, and findings
that only a reviewer can spot go in `quality/manual-findings.yml`. Later stages
add narrative-to-structure conflict checks, duplication, links, and example
validation.

## Website (to come)

A static, multi-page site:

- a document tree on the left;
- a card or structured artifact on the right;
- breadcrumbs, permanent links, and previous/next;
- quality findings shown in place;
- card-level comments through AIRA InteropHub.

The presentation is a project-owned theme (`site/theme/`) for joint CDC/AIRA
branding.

## Narrative and IGAMT comparison

`tools/check_cards.py` also compares the cards with `model/` (`tools/compare_structure.py`):

- **Automated, on every build:** field references that do not exist, field names that differ from the
  profiles, codes not in the bound value set, Figure 20 against the OBX co-constraint tables
  (transcribed in `quality/transcriptions/fig-20.yml`), and checks of the export itself (conditional
  usage without a predicate, empty or placeholder value sets, reused constraint IDs, inconsistent
  co-constraint rows).
- **Reviewed:** judgements recorded with their evidence in `quality/igamt-review.yml` (conflicts, gaps,
  export defects, questions, and confirmed matches), each saying who acts: the narrative, IGAMT, or a CDC decision.

The site shows these findings on the sections they concern, adds a "Message structure" panel to every
section that mentions fields, and publishes the comparison report at `quality/igamt/` with the
change requests for IGAMT. All findings are downloadable as `quality/findings.csv`.

## Chapter 7, Message Infrastructure

`tools/site_structure.py` generates chapter 7 from `model/`: a page per message profile (segment tree,
slicing, message- and group-level constraints), per segment (every field across all flavors) and
segment flavor, per data type, per value set (codes and where it is bound), and the OBX co-constraint
tables per profile. Field references (RXA-20), profile codes (Z22), and value set IDs in the narrative
link to these pages, and each segment page lists the sections that discuss its fields. Export
findings appear on the page they concern. The site test fails on any broken internal link.

## Example messages

`tools/import_examples.py` reads CDC's example list (xlsx) and the drafted samples (docx), both kept
local, and writes one file per example to `examples/`. Each example is matched to its row in the list
and, through the row's sub-section, to the cards it illustrates. Corrections go in
`examples/_meta/overrides.yml`.

Most drafted examples are clips: only the segments that matter. `tools/hl7msg.py` completes each clip
from a base message (the VXU, Z32/Z42, or ACK base in `examples/_meta/bases.yml`), so every example is
a whole message. The site highlights the clipped segments and marks the fields that differ from the
base.

`tools/example_checks.py` checks every example against the IGAMT profiles in `model/` on each build:
- the profile and message type;
- segments, required and unsupported fields and components, conditional usage from the predicates,
  and repetitions;
- codes in bound value sets, and date and time formats;
- segment and data type conformance statements, and the OBX co-constraints.

Problems an example inherits from its base are reported once, on the base. Message-level and
group-level conformance statements are not evaluated yet.
