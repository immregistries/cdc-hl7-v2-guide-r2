# Card format

The narrative of the guide is a **tree of cards**. A card is one entry in the
guide's table of contents: a short, focused unit with a fixed set of
resources. Parent cards introduce a topic, and their children cover it.

Cards live in `cards/` as nested folders. A folder's position among its
siblings comes from its two-digit prefix. The rest of the folder name is the
card ID, shortened to 32 characters to keep paths short. Its identity comes
from the **card ID** in `card.yml`, never from the folder name, title, or
number.

```text
cards/
  INDEX.md                                 generated table of contents (do not edit)
  _meta/                                   conversion bookkeeping (see below)
  04-data-standardization-and-integration/
    card.yml
    narrative.md
    05-patient-information/
      card.yml
      narrative.md
      01-patient-identifiers/
        card.yml
        narrative.md
        fig-21.png
        02-primary-patient-identifier-for-exchange/
          card.yml
          narrative.md
          statements.yml
```

## `card.yml`

```yaml
id: primary-patient-identifier-for-exchange   # permanent; never reused
title: Primary Patient Identifier for Exchange
figures:                                     # optional, in display order
  - id: fig-21
    file: fig-21.png
    number: 21
    caption: 'Patient Identifier Comparison: Medical Record Number vs. State Registry Identifier'
    alt: ''                                  # short text alternative (to be written)
tables:                                      # optional, in display order
  - id: table-1
    file: table-1.md
    caption: ''
references: [7]                              # optional; numbers in data/references.yml
glossary: key-terms                          # optional; card renders a glossary data set
related:                                     # optional; managed links by ID, grouped
  guidance: [assigning-authority-and-identifier-namespace]
  structures: [seg-pid-iz01--f3]
  vocabulary: [vs-hl70203-iz]
  examples: []
  external: []
```

Only `id` and `title` are required. Empty collections are omitted.

## `narrative.md`

The narrative is one to three paragraphs on one topic. Limited Markdown is
allowed: emphasis, links, and simple lists. It has no headings: a new heading
means a new card. Conformance verbs (SHALL, SHOULD, MAY) do not belong in
narrative paragraphs; they go in `statements.yml`.

## `statements.yml`

An ordered list of conformance statements.

```yaml
- id: primary-patient-identifier-for-exchange--s1   # permanent; never reused
  verb: SHALL
  actor: Sending systems
  text: Sending systems SHALL submit a primary exchange identifier for each patient and SHALL use the current identifier consistently in update and query transactions.
```

- `verb` is the first conformance verb in the statement. If the statement has
  more than one, `verbs` lists them all, and the quality checks flag it.
- `actor` is who the statement binds. It is empty when it cannot be
  determined.
- A statement keeps its ID when it is reordered or reworded. A new statement
  takes the next unused number.

## IDs

- **Card IDs** are lowercase words joined by hyphens, at most 80 characters,
  unique across the guide, and permanent. A retired ID is never reused.
- **Statement IDs** are `<card-id>--s<n>`.
- Every ID can serve as a link target and as a comment anchor.

## `_meta/`

Until cutover, cards are generated from the CDC narrative draft by
`tools/convert_narrative.py`. Files in `_meta/` keep IDs stable across
re-runs and record human decisions:

| File | Purpose | Edited by |
|---|---|---|
| `ids.yml` | Card ID ledger: each card's source trace (IGAMT section bookmark, or heading path) and ID, including retired IDs | Converter (do not edit by hand, except to fix a mis-match) |
| `statement-ids.yml` | Statement ID ledger per card | Converter |
| `overrides.yml` | Conversion rules: sections not to split, glossary sections, context-heading names, alt text, and similar | **People** |
| `conversion-notes.yml` | What the converter noticed (statements mixed into prose, heading variants, …); read by the quality checks | Converter |
| `source.yml` | Which draft the cards came from (file name and hash) | Converter |

Before cutover, **do not edit card files by hand**: the next conversion
overwrites them. Put lasting changes in `overrides.yml`. After cutover, the
converter is retired, and card files are edited directly.
