IIS must support state and federal policy, but they must do so using the correct HL7 v2 mechanisms. Policy expectations describe what programs want providers and systems to accomplish; HL7 v2 conformance describes what must appear in a message. Confusing these two leads to wasted effort, inconsistent implementations, and unreliable data. IIS authors should translate policy into HL7 v2 deliberately, using HL7's definitions, not policy language, to determine conformance.

IIS should support policy by:

**Representing program requirements accurately using RE** when that is the technically correct HL7 expression. Most policy requirements translate to "Required to Support," not to "Required and must always be populated."

**Explaining in the guide why R is reserved for structural necessities**, fields without which the IIS cannot safely store or understand a record.

**Documenting program expectations outside the HL7 conformance tables** (e.g., in narrative sections, onboarding guidance, or data quality documentation) instead of forcing program rules into message structure.

**Ensuring that HL7 requirements reflect operational reality**, what the IIS truly needs to store, process, or interpret, not what the program hopes to encourage through compliance pressure.

**Relying on data quality programs, not conformance verbs, to improve data completeness**, using onboarding, monitoring, and follow-up rather than distorting HL7 to force behavior.

For example, an IIS may accept a vaccination record that omits information expected by program policy, while returning an ACK warning that identifies the missing data. This approach records the vaccination while providing actionable feedback to the submitting system. Data-quality expectations can then be reinforced through onboarding, monitoring, and follow-up, rather than by rejecting messages or reclassifying RE fields as R.
