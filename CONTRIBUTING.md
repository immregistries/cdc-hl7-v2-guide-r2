# Contributing

This is a working draft maintained by AIRA with CDC.

- **Comments on the guide:** once the review site is published, use the
  comment control on each section. Until then, contact the maintainers.
- **Content changes:** until the card tree becomes the source, the narrative is
  regenerated from CDC's draft. Do not edit files under `cards/` by hand, since
  the next conversion would overwrite them. Conversion rules belong in
  `cards/_meta/overrides.yml`.
- **Decisions on quality findings** go in `quality/dispositions.yml`, keyed by
  finding ID.
- **Tools:** keep them deterministic (the same input gives byte-identical
  output), run `python -m unittest discover -s tests`, and do not commit source
  files (Word, IGAMT export, examples).
