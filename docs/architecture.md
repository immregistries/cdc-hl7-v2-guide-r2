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
| Conformance structure (profiles, segments, data types, value sets, constraints, co-constraints) | IGAMT | `model/` (to come), normalized from the IGAMT export |
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
