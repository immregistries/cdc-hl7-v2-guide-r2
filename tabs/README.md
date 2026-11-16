# Technical Advisory Bulletins (TABs)

Published TABs for the HL7 v2.5.1 Implementation Guide for Immunization Messaging, downloaded from the
[AIRA repository](https://repository.immregistries.org/resource/tab-resources/). TABs are published community
specifications, so unlike the narrative draft and the IGAMT export, they are kept here as sources.

- `*.pdf`: the TABs as published, renamed `<publication month>-<topic>.pdf`
- `text/*.txt`: text extracted with `pdftotext -layout -enc UTF-8`, for searching and comparison

`data/tabs.yml` lists each TAB with its published URL and the guide sections it affects. The comparison of each TAB with
the guide is in `quality/tabs/<id>.yml`, and the site shows it under **TAB Comparison**.

To add or update a TAB: put the PDF here, extract its text, add or update its entry in `data/tabs.yml`, and review the
comparison.
