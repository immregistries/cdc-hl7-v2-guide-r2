VXU messages are used when a submitting system needs to inform an IIS of a change to a patient's immunization record. This includes:

Reporting newly administered vaccinations

Recording historical vaccinations documented later

Correcting or deleting previously submitted vaccination events

In limited cases, transmitting patient demographic information when closely tied to immunization reporting

VXU messages are unsolicited: they are sent without a prior request from the IIS and rely on IIS-side processing to deduplicate patients and vaccination events and to merge incoming data into a consolidated record.

VXU messages are not intended to support workflows where information is collected independently of immunization activity (e.g., changes in housing status, occupation, or social conditions).

Alternative HL7 v2 mechanisms such as ADT messages are better suited for those use cases and are outside the scope of this guide.
