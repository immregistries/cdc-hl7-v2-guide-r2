# CDC feedback on the first draft output (23 November 2026)

A point-in-time record of CDC's first reactions to the draft site and PDF, and how we plan to approach
them. **Nothing here is agreed yet.** It is preparation for a call with CDC on 24 November 2026 ("HL7 IG
Output"). Record what was decided there, then turn the agreed parts into work.

## What CDC asked for

After reviewing the IG output, CDC asked to talk through:

1. A way to mark errors, warnings, and notes as complete on the IG webpage.
2. Formatting changes to the IGAMT output and the PDF.
3. The IG as a Word document (instead of a PDF), so they can edit it easily.
4. A timeline for sharing a new draft before the 9 December SISC meeting.

They also have ideas about editing functionality, but want to get the IG itself in good shape first.

## How we want to approach it

### 1. Feedback on quality findings, with a visible life cycle

The author (currently AIRA) owns fixing findings. CDC reviewers do not close them. The cycle is:

1. A reviewer comments on a specific finding: what they think the resolution is, or that it should be
   waived because the text is intended.
2. The author fixes the section (or CDC fixes IGAMT, for IGAMT findings), or records a waiver in
   `quality/dispositions.yml`.
3. The author re-runs the build. The finding disappears, stays, or shows as waived.
4. The reviewer verifies.

What exists today: comments attach to a whole page or card (see [comments.md](comments.md)), and topic 52
editors (CDC's editors are topic Champions) see the author view. What is missing:

- **Comments on a single finding.** Each finding needs its own comment anchor, the way statements and
  figures have one now.
- **Stable finding IDs** across runs, so a comment stays attached to its finding after the text around it
  changes. Check this before building anything.
- **A visible life cycle.** After a re-run, each commented finding shows its state: open, resolved (no
  longer present), or waived (with the reason from `dispositions.yml`).
- **Waiver requests.** A reviewer can say "intended, suppress this". The author decides and records the
  waiver.

Longer term, CDC may take over authorship. That needs CDC to be comfortable with the tools and process,
and to have approval to use AI coding agents to edit and republish. Until then, AIRA makes the changes.

### 2. Formatting of the IGAMT output and PDF

This was the first draft. Collect specific examples from CDC (page and what is wrong). Also check the
generated output against the color guidance CDC has since sent (see
[cdc-color-proposal.md](cdc-color-proposal.md)). Fixes go into the generators (`tools/build_pdf.py`,
`tools/site_structure.py`, the theme), never into an output file.

### 3. Word: an input, not the master

Direction: **this repository is the master** (source first). The long-term plan, once CDC agrees, is for
the Markdown cards to be the source of truth, with Word, PDF, HTML and other outputs generated from them.
A problem in an output is fixed by changing how that output is generated.

Today the narrative is still converted from CDC's Word draft (`tools/convert_narrative.py`). That makes
two masters as soon as anyone fixes a card directly: the next conversion would overwrite the fix. This
needs to be settled with CDC.

CDC learned about this process last week, and a Word file they can adjust gives them confidence. So we
will not refuse Word. Instead:

- Generate a Word edition from the source for review.
- Treat edits in it (tracked changes and comments) as **feedback**: extract them and apply them to the
  source. The next build reflects them. Do not keep the Word file as a maintained document.
- Neither the Word export nor the tool that reads tracked changes exists yet.

On "Word, then PDF": we think that is the wrong paradigm here. Manual formatting in Word is lost on every
regeneration. Chapter 7 must come from IGAMT, not from hand edits. Whatever CDC would change in Word is
really a formatting requirement for the generated PDF. If the generators are fixed once, every future
build benefits. The PDF should always come from the source.

### 4. Timeline for 9 December SISC

Deferred until after the call.

## Questions for the call

1. When you picture editing in Word, is it wording, formatting, or both?
2. What is wrong in the PDF and IGAMT output? Specific pages, please.
3. Would a generated Word file you mark up with tracked changes, which we apply to the source, meet the
   need?
4. Can this repository be the master from now on, so narrative edits no longer come from the original Word
   draft?
5. For a finding you think is fine as written, is a comment saying "intended, suppress it" enough for the
   author to record a waiver?

## Decisions from the call

_To be filled in after 24 November 2026._
