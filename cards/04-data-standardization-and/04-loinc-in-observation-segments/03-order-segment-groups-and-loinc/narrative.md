Immunization messaging uses Order Segment Groups as logical containers for transmitting related clinical and administrative information. An **Order Segment Group** consists of a coordinated set of HL7 v2 segments, ORC, RXA, optional RXR, and one or more OBX segments, that together convey a coherent unit of meaning.

The term Order Segment Group originates from HL7 v2's historical use of this structure to represent pharmaceutical orders and medication administration events within inpatient workflows. In immunization messaging, this same structure is repurposed to convey completed immunization events, non-administered doses, patient-level observations, and clinical decision support outputs exchanged between submitting systems and IIS in VXU messages, and returned by IIS in RSP messages.

Although Order Segment Groups have a defined on-the-wire structure, the names used in this guide for different Order Segment Group flavors are conceptual only. These names do not appear in the message itself. Instead, they provide a consistent way to describe how OBX segments are grouped, interpreted, and constrained based on the clinical or operational context they represent.

Within an Order Segment Group:

ORC and RXA establish the contextual anchor for the group.

RXR, when present, provides route and site information.

OBX segments carry supplemental observations that describe, qualify, or extend the meaning of the group.

Grouping conveys meaning that cannot be derived from individual OBX segments alone. The same LOINC-coded observation may appear in multiple Order Segment Group flavors, but its interpretation depends on the group in which it is placed. For example, an observation describing immunity, eligibility, or reaction may have different implications depending on whether it appears under an administered immunization event, a non-administered dose, or a patient-level observation group.

For this reason, this guide defines a fixed set of Order Segment Group flavors. Each flavor represents a specific use case and establishes expectations for:

Which LOINC-coded OBX segments may appear

Whether those OBX segments are required, expected, or optional

How the observations are interpreted in context

The use of LOINC-coded OBX segments outside the defined Order Segment Group flavors is not prohibited; however, such usage is out of scope for this guide. Observations sent outside the group contexts defined here have no standardized meaning and must be interpreted based on local or bilateral agreements. LOINC codes are not intended to be arbitrarily combined or repositioned to convey meaning beyond what is explicitly defined in this guide.

The sections that follow describe each Order Segment Group flavor, its purpose, and the LOINC-coded observations expected within it. Detailed semantic rules for clinical decision support, such as evaluation and forecast logic, are defined in later sections of this guide and build upon the grouping concepts established here.
