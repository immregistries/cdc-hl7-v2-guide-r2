# MIROW best practice guides

Operational best practice guides for immunization information systems (IIS), published by AIRA's Modeling of Immunization
Registry Operations Workgroup (MIROW) from 2005 to 2022, plus two closely related guides (CDC's patient-level
deduplication best practices and AIRA's patient status implementation guide). MIROW no longer meets, so the set is
complete. The guides do not define messages, but deduplication, record consolidation, patient status, inventory
decrementing, and data quality all depend on what arrives in VXU and QBP messages, so this guide should agree with them,
use the same terms, and point to them where they apply.

- `*.pdf`, `*.xlsx`: the documents as published, renamed `<publication month>-<topic>.<ext>`
- `text/*.txt`: extracted text, for searching and comparison (PDF: `pdftotext -layout -enc UTF-8`; Excel: each sheet, one
  row per line, cells separated by tabs)

`data/mirow-guides.yml` lists each guide with its resource page, its published copy, and how it relates to earlier
versions. Comparisons with the guide are to come.

Only the current full guide on each topic is kept. Mini-guides, Spanish and French versions, slides, and guides that a
later guide replaced are left out; `data/mirow-guides.yml` names the guides each one replaced. These were found by a scan
of the AIRA repository; see `docs/aira-repository-scan.md`.

Most copies were downloaded from the [AIRA repository](https://repository.immregistries.org/) in November 2026. The
common vocabulary and principles and business rules pages no longer offer their files, and CDC's deduplication guide has
moved, so those copies come from the repository's file store and the Internet Archive; `data/mirow-guides.yml` says which.
