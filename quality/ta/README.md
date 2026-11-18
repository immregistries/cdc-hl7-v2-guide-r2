# TA Questions: assessing the guide

Implementers have asked AIRA's technical assistance (TA) service about HL7 v2 immunization messaging for about ten
years. These files record whether the **current guide** answers each of those questions. The aim is to find gaps in the
guide, not to check the past answers. The pages appear on the website in the author view only (TA Questions).

| Path | What it is | Edited by |
|---|---|---|
| `index.yml`, `pages/<page>.yml` | The questions, each with the answer given at the time, grouped by segment and field or by topic | `tools/import_ta.py` only (never by hand) |
| `assess/<page>.yml` | Whether the guide answers each question, keyed by question ID | By hand (or an agent), one file per page |

Who asked is left out of everything here (see `tools/import_ta.py`). Keep it that way in the assessments too: no
jurisdictions, IIS vendors, or people. EHR products may be named.

## Status

| Page | Questions | Assessed |
|---|---:|---|
| msh | 39 | Done (2026-11-17), the worked example |
| the other 30 pages | 877 | Not yet |

Run `python tools/build_site.py --edition author` and open TA Questions to see the counts per page.

## How to assess a page

1. Read `pages/<page>.yml` and `assess/msh.yml` (the pattern to follow).
2. For each question, find what the guide says: the cards in `cards/` (search for the fields, codes, and topics), the
   conformance statements, chapter 7 (`model/`: usage, cardinality, value sets, conformance statements, co-constraints),
   the examples, and the TABs already folded in (`quality/tabs/`). Judge the current draft only.
3. Write `assess/<page>.yml`. Assess every question on the page.
4. Check: `python -m unittest tests.test_convert.TaQuestionsTest` (every guide reference must exist), then
   `python tools/build_site.py --edition author` and look at the page and the Quality review list.

### The file

```yaml
# How well the guide answers the TA questions on the <Title> page. Keyed by question id (pages/<page>.yml).
# result: answers | appeal | partial | gap | differs | out-of-scope. guide: card, statement (<card>--sN) or figure IDs;
# the first one is where a finding is attached (where the answer belongs).

reviewed: YYYY-MM-DD
against: narrative draft of <date> and IGAMT export of <date>     # from cards/_meta/source.yml and model/source.yml
summary: >-
  One paragraph: what the guide answers well, the recurring gaps, and any past answers the guide now contradicts.

items:
  ta-q03-098:
    result: gap
    severity: note            # optional; overrides the default for the result
    guide: [message-structure-and-terminology]
    note: >-
      What the guide says or lacks, with the specific section, statement, or profile element.
    recommendation: >-
      The change to make, and where: a sentence, statement, or section to add or correct.
```

### Results

| Result | Use when | Default finding |
|---|---|---|
| `answers` | The guide (narrative, statements, or IGAMT profiles) answers it directly | none |
| `appeal` | The answer follows from the guide's rules or principles, but the guide does not say it | note |
| `partial` | The guide answers part of it | warning |
| `gap` | The guide does not address it | warning |
| `differs` | The guide answers differently from the past answer: a deliberate change, or a past answer to correct | note |
| `out-of-scope` | Local policy, transport details outside the guide, testing tools, or one product | none |

### Conventions (from MSH)

- **`guide`:** give it for every result except `out-of-scope`, and for `gap` too: the card where the answer *belongs*.
  The first entry is where the finding appears, so put the best home first. Prefer a statement ID (`<card>--s2`) when
  one statement answers or should answer it. A finding appears only when `guide` is given.
- **`note`:** say what the guide says, and where (section number and title, statement, IGAMT conformance statement such as
  IZ-13, or value set). For `answers`, a note is optional; add one when the answer is only in IGAMT, or is newly clear.
- **`recommendation`:** for `gap`, `partial`, `appeal`, and `differs` when the guide should change. Be concrete. When the
  same fix answers several questions (for example "add a Message Header section"), say so the same way each time.
- **`severity`:** leave the default unless there is a reason. Raise a `gap` to `issue` only when implementers would get it
  wrong without the answer. Lower to `note` for minor gaps.
- **`differs`:** say whether the change looks deliberate (the guide is clearer or stricter) or whether the guide may be
  wrong. A conflict inside the guide itself (narrative vs IGAMT) is worth calling out in the note.
- Questions in the same group often share an answer: assess each, but reuse the reasoning.

## Plan for the remaining pages

Work in batches, one fresh session (or agent) per batch, so each has room to read the guide closely:

| Batch | Pages | Questions |
|---|---|---:|
| 1 | msa, err, qak, qpd, rcp | 66 |
| 2 | pid, pd1 | 103 |
| 3 | nk1, pv1, in1, orc, nte | 33 |
| 4 | rxa (first half of the groups) | ~80 |
| 5 | rxa (second half) | ~78 |
| 6 | obx (first half of the groups) | ~74 |
| 7 | obx (second half), rxr | ~94 |
| 8 | acknowledgement-and-error-handling, message-structure-and-cardinality, version-and-ig-interpretation, query-and-response-behavior, patient-matching-and-deduplication, bidirectional-exchange | 120 |
| 9 | code-sets-and-vocabulary, immunization-evidence-refusals-immunity-contraindications, vfc-and-funding-eligibility, data-quality-and-validation, local-profiles-and-jurisdictional-constraints | 94 |
| 10 | transport-and-connectivity, conformance-testing-and-validation-tools, onboarding-and-interface-testing, other | 135 |

Batches 1 to 7 (segments) come first: they map most directly to sections of the guide. Several can run at once, as
long as each writes only its own `assess/` files. RXA and OBX are split by group, so the two halves go into one file:
run the second half after the first, or have each write its items and merge them.

**To start a batch** (a new Claude Code session in this repository, or an agent):

> Read quality/ta/README.md and assess the TA questions for batch N (pages: ...). Follow assess/msh.yml as the pattern.
> Write only quality/ta/assess/<page>.yml for those pages, run the TA test and an author-edition build, and report the
> results and the main gaps for each page. Don't commit.

**When all batches are done:** one consistency pass across the pages: the same kind of question gets the same result,
repeated recommendations use the same wording (and point to the same section), severities are even. Then build, test,
commit, and push. Afterwards, the gaps feed the next narrative draft: the Quality review list (rule `ta-review`) has
them by section.
