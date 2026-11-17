# Comparison with Release 1.5

Published as "Changes from Release 1.5" (`r15/index.html`). The baseline is explained in
[prior/release-1.5/README.md](../../prior/release-1.5/README.md): NIST's conformance profiles for format and validation,
plus the guidance in the 2018 narrative.

| Part | How | Here |
|---|---|---|
| Format and validation | Computed from the two sets of profiles (`tools/diff_r15.py`) | `config.yml` (external code systems not compared) |
| Narrative guidance, pass 1 | Reviewed by hand: chapters 1-3, profile introductions and dynamic definitions (5-12), batch (13), Appendix B guidance, Appendix C | `narrative/*.yml` |
| Narrative guidance, pass 2 | Reviewed by hand: the field notes and comments in the 2018 segment tables (chapters 5-12) and data type chapter (4) | `narrative/f*.yml` |

## Pass 1: the narrative

One item per piece of guidance, in 2018 document order. Each item has a result: `same`, `expanded`, `changed`, `dropped`,
`partial`, `format` (the profiles govern it), or `context`. The fields are listed at the top of
`narrative/01-02-introduction-and-actors.yml`. `tools/r15_narrative.py` checks results, IDs, and that every guide
reference names an existing card or statement; the site build fails otherwise.

## Pass 2: field notes

The 2018 segment and data type tables carry a comment column and field definitions (about 150 pages). Most notes restate
format (usage, lengths, value sets) that the profiles now carry, or repeat the narrative. The second pass read every note
but recorded an item only when the note:

- adds guidance not in pass 1 and not carried by the profiles (for example, how to mark a historical record in RXA-9), or
- conflicts with this guide or with a pass 1 item.

Notes that only restate format or duplicate the narrative are counted per segment under `read` (notes, format,
duplicate), not itemized, so the record shows that they were read; `tools/r15_narrative.py` checks that the counts add
up. Items use the same fields and results, with IDs `r15-f-<segment>-NN`.

| File | 2018 pages | Notes read | Items |
|---|---|---|---|
| `f1-z22-segments.yml` | 80-130 | 100 | 21 |
| `f2-ack-query-response-segments.yml` | 135-282 (most repeat Z22) | 155 | 2 |
| `f3-data-types.yml` | 35-74 | 34 | 3 |
