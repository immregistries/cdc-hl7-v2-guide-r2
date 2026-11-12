Patient status values transmitted in HL7 v2 messages reflect the provider's perspective, not the IIS's jurisdictional view of the patient. An "active" designation indicates that the provider considers the patient currently under their care for immunizations. An "inactive" designation indicates the provider no longer considers the patient part of their active population. A deceased designation signals that immunization outreach should cease.

Because most interfaces submit data only at the time of vaccination, providers rarely send explicit updates when a patient becomes inactive. As a result, absence of an inactive status should not be interpreted as confirmation that the patient remains under active care.

Patient status values, when present, SHALL be interpreted as provider-reported information.
