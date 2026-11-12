Represents observations that apply to the patient as a whole and are not associated with any specific immunization event. All patient-level observations SHALL be conveyed within a single Patient Observation Order Segment Group per message.

If multiple patient-level observations are reported, they SHALL be included within the same group. Creating multiple Patient Observation groups does not convey additional meaning. If observations need to be logically linked, OBX-4 SHALL be used.

The following LOINC-coded observations may appear in OBX segments within this group:

Adverse reaction not attributable to a specific vaccination event - LOINC **31044-1**

Serological evidence of immunity - LOINC **75505-8**

Presumed evidence of immunity (history of disease) - LOINC **59784-9**

Patient condition - LOINC **75323-6**

Date of condition onset - LOINC **85585-8**

Date of condition abatement - LOINC **88878-4**

See Section 4.8.4, Adverse Event, for adverse-event semantics and reporting workflows.
