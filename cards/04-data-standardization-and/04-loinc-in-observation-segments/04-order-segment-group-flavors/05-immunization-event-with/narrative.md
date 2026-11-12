Represents a vaccination event along with evaluation results produced by a Clinical Decision Support (CDS) engine. This group combines vaccination history with assessment of how the dose was evaluated against immunization recommendations.

For combination vaccines, multiple evaluation sets may be included-one per evaluated target disease. Evaluation semantics and conformance requirements are defined in the Clinical Decision Support sections of this guide.

The following LOINC-coded observations may appear in OBX segments within this group to convey evaluation results:

Vaccine type - LOINC **30956-7**

Dose validity - LOINC **59781-5**

Reason for validity - LOINC **30982-3**

Series name - LOINC **59780-7**

Total number of doses in series - LOINC **59782-3**

Dose number of evaluated event - LOINC **30973-2**

Schedule used - LOINC **59779-9**

See Section 4.7, Clinical Decision Support, for examples and detailed guidance on when and how evaluation results are produced and returned.
