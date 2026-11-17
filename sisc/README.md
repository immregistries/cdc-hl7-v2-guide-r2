# SISC guidance documents

Guidance documents for Release 1.5 of the HL7 v2.5.1 Implementation Guide for Immunization Messaging, published by AIRA
and CDC through AIRA's Standards and Interoperability Steering Committee (SISC) before the Technical Advisory Bulletin
(TAB) series began in 2024. They were downloaded from the [AIRA repository](https://repository.immregistries.org/). Like
the TABs (see `tabs/`), they are published community guidance, so they are kept here as sources.

A few related documents published by AIRA or the Immunization Integration Program, rather than by SISC, are kept here
too (their entries in `data/sisc-guidance.yml` say so). Most of these were found by a scan of the AIRA repository; see
`docs/aira-repository-scan.md`.

- `*.pdf`, `*.docx`, `*.xlsx`: the documents as published, renamed `<publication month>-<topic>.<ext>`
- `text/*.txt`: extracted text, for searching and comparison (PDF: `pdftotext -layout -enc UTF-8`; Word: the text of
  each paragraph; Excel: each sheet, one row per line, cells separated by tabs)

`data/sisc-guidance.yml` lists each document with its published URL and the guide sections it affects. The comparison of
each document with the guide is in `quality/sisc/<id>.yml`, and the site shows it under **SISC Guidance**.

Only published documents are kept here.

To add or update a document: put the published file here, extract its text, add or update its entry in
`data/sisc-guidance.yml`, and review the comparison.
