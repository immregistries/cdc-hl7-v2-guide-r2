# AIRA repository scan

In November 2026, the [AIRA repository](https://repository.immregistries.org/) was searched for published documents
that bear on this guide, beyond the TABs and the SISC guidance documents already compared. The search used a November
2024 snapshot of the repository's database and file store, so it covers older documents well; documents added since
then need a separate check.

## Method

1. Of about 1,920 resources, 1,845 were published or archived and not deleted.
2. Resources tagged as presentations, national meeting presentations, webinars, videos, infographics, meetings, or
   newsletters were set aside, leaving about 490. (One MIROW guide, Decrementing Inventory via Electronic Data Exchange,
   carried a meeting tag and was put back.)
3. Each remaining resource's title, description, and categories were read, and those that bear on message content,
   conformance, code sets, or the IIS processes that depend on messages were shortlisted.
4. Public comment letters, policy and legal documents, coverage assessment and reminder/recall guides, journal
   articles, and earlier versions of the guide itself were left out.

## What was added

- **MIROW guides** to `mirow/` (`data/mirow-guides.yml`).
- **SISC and related HL7 guidance** to `sisc/` (`data/sisc-guidance.yml`).

## Kept for later

Not added as sources yet, but likely useful. Numbers are repository resource IDs.

### Specifications and guides alongside the guide

| ID | Date | Document | Why |
|---|---|---|---|
| 858 | 2019-01 | AIRA IIS Functional Guide, Vol. 1: Query and Response; Vol. 2: CDC-Endorsed Data Elements | Functional requirements behind QBP/RSP and the core data elements |
| 1315 | 2020-12 | IZ Gateway HL7 Implementation Guide v1.1; IZ Gateway Portfolio Technical Specifications for EHRs v1.1 (archived) | A profile of this guide for the IZ Gateway |
| 1079 | 2018-12 | IIS-EHR Interoperability: Common Areas of Variability Based on Jurisdictional Law/Policy | Input to the survey of local implementation guides |
| 1050 | 2018-11 | Onboarding Consensus-Based Recommendations | Onboarding expectations for submitters |
| 601 | 2017-02 | Data Validation Guide for the IIS Onboarding Process | Message validation during onboarding |
| 824 | 2017-09 | IIS Data Quality Practices: Monitoring and Evaluating Data Submissions | Ongoing checks on incoming messages |
| 1565 | 2023-01 | Query Response Workflow Functionalities Catalog (Immunization Integration Program) | Query and response behavior in EHRs and IIS |
| 1564 | 2023-01 | Query Response Aggregate Measures for Multiple Matches (Immunization Integration Program) | Measuring multiple-match outcomes |
| 1310 | 2020-11 | IIP Collaborative Transport Recommendations | Transport |
| 1021 | 2018-09 | Message Quality Evaluation (MQE) Tool Implementation Guide (archived) | Message quality detections |
| 1087 | 2017-08 | IIS Functional Standards v4.0 (CDC) | Functional standards that cite the guide |

### Measurement and Improvement measures and tests

For a desk comparison with the guide (see the proposed AART comparison).

| ID | Date | Document |
|---|---|---|
| 603 | 2019-09 | Measures and Tests for Assessment: Message Submission and Acknowledgement |
| 604 | 2024-09 | Measures and Tests for Assessment: Query and Response |
| 1921 | 2024-11 | Measures and Tests for Assessment: Patient Matching HL7 (draft) |
| 1247 | 2024-09 | Measures and Tests for Assessment: Data Quality Incoming/Ongoing |
| 785 | 2019-05 | Measures and Tests for Assessment: Transport |
| 891 | 2020-02 | Measures and Tests for Assessment: Clinical Decision Support |
| 879 | 2021-06 | IIS Validation Measures and Tests for Submission and Acknowledgment |
| 880 | 2019-05 | IIS Validation Measures and Tests for Query and Response |
| 1361 | 2021-08 | IIS Validation Measures and Tests for Data Quality Incoming/Ongoing |
| 870 | 2019-05 | IIS Validation Measures and Tests for Transport |
| 1246 | 2020-02 | IIS Validation Measures and Tests for Clinical Decision Support |

### Information requests

AIRA's summaries of member answers to a question from one jurisdiction. They show how IIS actually handle a topic, so
they are evidence for the survey of local implementation guides rather than sources to compare.

| ID | Date | Topic |
|---|---|---|
| 864 | 2018-03 | Patient inactivation |
| 896 | 2018-06 | Patients without an address |
| 1033 | 2018-10 | Contraindication for all vaccines |
| 849 | 2017-10 | CDC WSDL usage and management |
| 1103 | 2019-06 | Vaccine administration errors |
| 1111 | 2019-07 | Recording international vaccines |
| 1198 | 2019-08 | Combinations of CVX and reaction code |
| 1224 | 2019-10 | Health plans using QBP to query members for HEDIS measures |
| 1276 | 2020-05 | Temporary names for newborns |
| 1309 | 2020-10 | Exemptions |
| 1330 | 2021-02 | Capture of race and ethnicity data |
| 1442 | 2022-02 | Missing patient-reported doses |
| 1509 | 2022-05 | Mother's maiden name collection |
| 1533 | 2022-08 | Insurance HL7 segments |
| 1709 | 2023-08 | Transgender youth, alias, and gender change |
| 1729 | 2023-10 | IIS maintenance of vaccine lot numbers |

### Considered and left out

- Release 1.0 to 1.4 of the guide (2010 to 2012) and the HL7 2.3.1 implementation guides (2006): history only.
  Release 1.5, its addendum, and the 2018 update are already in `prior/release-1.5/`.
- MIROW guides with little bearing on messages: Reminder/Recall (2009), Collaboration with Vaccines for Children (2011),
  and Business Continuity Planning (2019).
- MIROW guides replaced by later ones (see `data/mirow-guides.yml`), mini-guides, translations, and slides.
