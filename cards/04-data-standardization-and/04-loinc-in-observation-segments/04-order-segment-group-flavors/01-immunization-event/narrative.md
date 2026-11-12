Represents an administered or historical vaccination dose. This Order Segment Group is used to report vaccination events to the IIS in a VXU message and to return vaccination history from the IIS in an RSP message. All observations in this group provide additional information about the vaccination dose represented by the RXA segment.

The following LOINC-coded observations may appear in OBX segments within this group:

Patient eligibility status (required for new administrations) - LOINC **64994-7**

Vaccine funding source (required for new administrations) - LOINC **30963-3**

Vaccine Information Statements (VIS) (required for most new administrations) - LOINC **69764-9**, **29769-7**

Adverse reaction reported (event observed or reported; causation not implied) - LOINC **31044-1**

Indication for administration - LOINC **59785-6**

Indication effective date - LOINC **88877-6**

Indication expiration date - LOINC **88879-2**

Free-text comment - LOINC **48767-8**

Adverse event semantics, causation assessment, and reporting workflows are described in Section 4.8.4, Adverse Event.
