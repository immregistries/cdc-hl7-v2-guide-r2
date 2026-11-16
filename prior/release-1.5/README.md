# Release 1.5 baseline

What this guide is compared against: the *HL7 Version 2.5.1 Implementation Guide for Immunization Messaging,
Release 1.5, 2018 Update*, as NIST built it into its testing tool.

| Part of the standard | Source of truth | Here |
|---|---|---|
| Format and validation: message structure, usage, cardinality, data types, lengths, value set bindings, conformance statements | NIST's conformance profiles in the [Immunization Test Suite Edition 2](https://tools.valitheus.com/immunization-edition2/#/doc), built by NIST from the 2018 Update. This is what systems were tested and certified against. | `nist/` (the profiles, merged), `model/` (normalized) |
| Guidance in the narrative | The [2018 Update PDF](https://www.cdc.gov/iis/technical-guidance/hl7.html) (`hl7_2_5_1_release_1_5__2018_update.pdf`, CDC) | `outline.yml` (bookmarks with page ranges), `text/guide.txt` (extracted text) |

The segment, data type, and code tables in the PDF are **not** used, and differences between them and the NIST
profiles are not reported: the NIST profiles are the baseline. Release 1.5 is represented as the NIST profiles plus
the guidance the narrative adds to them. NIST's reading of the guide is explained in its
*Errata and Clarifications Guidelines* (`NIST-Clarifications-SVAP-IZ.pdf`, on the same documentation page).

The PDF is not committed; get it from CDC. The NIST profiles are public and committed.

## Updating

```powershell
python tools/import_r15.py --download                # fetch the eight profiles from the test tool, then import
python tools/import_r15.py --pdf path\to\hl7_2_5_1_release_1_5__2018_update.pdf   # also the outline and text
```

`--pdf` defaults to `r15_pdf` in `inputs.json` and needs PyMuPDF. Everything in this folder except this README is
generated.
