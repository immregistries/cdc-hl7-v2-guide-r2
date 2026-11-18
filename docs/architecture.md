# Architecture

## Goals

1. **Usable and understandable.** Implementers find, understand, and link to
   what they need. Short sections, one topic each, with stable links and
   consistent placement of requirements, figures, examples, and related
   material.
2. **Visible quality, for the authors.** Automated and editorial checks run on
   every build, and their findings appear next to the content they concern, in
   the author view. Readers see the guide alone.
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
- quality findings shown in place, in the author view;
- card-level comments through AIRA InteropHub.

### Reader and author views

The guide is for readers. Material for the authors (quality findings, the comparisons with Release 1.5, IGAMT, the
TABs, SISC, MIROW, and the TA questions, the proposed analyses, and "How this guide is made") is marked author-only
(`tools/view.py`) and shown only in the author view. It is not secret (it is all in this public repository); it is
hidden because readers do not need it.

- **Who is an author.** InteropHub decides. The guide API (`GET /api/guide/{documentKey}`) returns
  `permissions.isAuthor` for the signed-in person: true for editors of the guide's topic, the same check that lets
  them dispose of and close comments. `site/theme/comments.js` caches the answer with the sign-in's expiry, and a
  script in each page's `<head>` turns the author view on before the page is drawn. Everyone else sees the reader
  view, with no switch and no mention of it.
- **Switching.** Authors get a Reader view / Author view button; the choice is remembered in the browser.
- **Editions** (`build_site.py --edition`): `draft` (default, as above), `author` (always on, for local previews),
  and `release` (no author material, author pages, or switch at all, for formal releases).

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

## Technical Advisory Bulletins

TABs are published community specifications that this guide is meant to fold in. The PDFs are kept in `tabs/` (they are
public, unlike the other inputs) and listed in `data/tabs.yml` with the guide sections they affect. Each TAB is compared
with the guide requirement by requirement in `quality/tabs/<id>.yml` (covered, in narrative only, reworded, partly covered,
missing, conflict, or added by the guide). `tools/tab_review.py` checks that every reference to a section, statement, or
figure exists, turns results that need attention into quality findings, and builds the **TAB Comparison** pages (below the
line in the contents, one menu item per TAB). Sections a TAB affects link to it, and section 6.2 lists every TAB.

## TA questions

The questions implementers have asked AIRA's technical assistance (TA) service are consolidated outside this repository
from AIRA's TA records. `tools/import_ta.py` publishes them into `quality/ta/` with who asked left out: no jurisdictions,
IIS vendors, or people, no individual records or source references, and years instead of dates. Replacements come from
`scrub.yml` in the TA folder (kept outside the repository, since it lists the names), and the import fails if a forbidden
name or a US state or territory name remains. EHR products are kept by name. Whether the guide answers each question is
assessed by hand in `quality/ta/assess/<page>.yml`; `tools/ta_review.py` turns gaps into findings and builds the
**TA Questions** pages, in the author view only.

## National ERR-5 code set

`tools/import_err5.py` imports AIRA's National Set of ERR-5 Application Error Codes (xlsx, kept local) into
`data/err5-codes.yml`. `tools/site_err5.py` publishes it as Appendix D, with each code's implementation priority, and marks
which codes the IGAMT value set HL70533_IZ01 has.
