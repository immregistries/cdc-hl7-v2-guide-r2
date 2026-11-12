LOINC and the HL7 v2 Observation (OBX) segment work together to provide a flexible mechanism for exchanging clinical information that does not fit cleanly into fixed HL7 v2 message fields. Historically, the OBX segment was designed to support laboratory reporting, a domain where new tests, measurements, and interpretations are introduced frequently and where results may vary widely in structure, datatype, and clinical meaning. To accommodate this variability, OBX was intentionally designed as a highly extensible structure capable of representing complex and evolving clinical concepts without requiring changes to the underlying message schema.

That same flexibility makes OBX well suited for immunization messaging. While most immunization data elements are carried in dedicated HL7 v2.5.1 fields, there are important concepts-such as eligibility determinations, funding source, contraindications, refusals, immunity evidence, and clinical decision support outputs-that are not supported by the base standard. OBX segments provide a standardized way to transmit this additional information without overloading or misusing core HL7 v2 fields.

Conceptually, each OBX segment follows a question-and-answer model:

**OBX-3 (Observation Identifier)** defines the question being asked.

**OBX-2 (Value Type)** defines the datatype of the answer.

**OBX-5 (Observation Value)** carries the answer itself.

In immunization messaging, OBX-3 always contains a LOINC code. LOINC serves as the controlled vocabulary that defines the meaning of each observation-effectively specifying what question is being asked. Although LOINC was originally developed for laboratory observations and remains heavily used in that context, it also includes codes that represent clinical, administrative, and public health concepts relevant to immunization workflows. This guide documents a specific subset of LOINC codes that IIS are expected to recognize and process for immunization messaging purposes.

The OBX segment can also be understood as a self-describing container. Rather than relying on the surrounding message context to infer meaning, each OBX segment explicitly declares the type of information it carries (via LOINC and datatype) and then carries the data itself. In this sense, OBX functions similarly to a "custom field," but one that is standardized, coded, and interoperable across systems.

This guide does not attempt to document all possible LOINC usage. IIS may support additional LOINC-coded observations for purposes beyond what is defined here. Conversely, IIS may receive OBX segments containing LOINC codes that are not recognized or not supported. In such cases, IIS are expected to ignore those OBX segments if they are not required for processing, without rejecting the message as a whole.

Within VXU messaging, OBX segments always appear as part of an Order Segment Group, following the ORC and RXA (and optionally RXR) segments. Although OBX segments are structurally tied to an ORC/RXA group, the information they convey may apply at different conceptual levels:

Event-level observations apply to a specific vaccination event and are grouped under the ORC/RXA that documents that administration.

Patient-level observations apply to the patient as a whole and are not tied to any specific vaccination event.

Because HL7 v2.5.1 does not support standalone observation groups, patient-level observations are transmitted using a placeholder ORC/RXA construct that satisfies structural requirements but carries no clinical meaning of its own. For these patient-level groups:

**RXA-20** is set to NA (not administered).

**RXA-5** is set to 998^No vaccination administered^CVX.

**ORC-3** is set to 9999.

The date in **RXA-3** can be populated with the current date but does not convey clinical timing for the observations.

In this construct, the ORC and RXA segments exist solely to provide a container for OBX segments; all meaningful information is conveyed in the OBX segments themselves.

The use of OBX segments in immunization messaging varies by concept. Some observations are required under specific circumstances, while others are optional and depend on system capability, workflow, or jurisdictional policy. The sections that follow define how OBX segments are grouped, where they appear in messages, and which LOINC-coded observations are supported, while deferring detailed semantic and clinical interpretation to later sections of this guide.
