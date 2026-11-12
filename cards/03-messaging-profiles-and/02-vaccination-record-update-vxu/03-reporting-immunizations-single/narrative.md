Submitting systems differ in how and when immunization events are finalized within clinical workflows. In some systems, vaccinations are completed, reviewed, and committed individually, while in others they are finalized at the end of an encounter or visit. As a result, the operational trigger for reporting immunizations to an IIS may occur on a per-vaccination basis or as a grouped submission for an entire encounter. The choice of reporting strategy is an implementation decision and does not alter the semantic meaning of the reported immunization events.

IIS do not control or prescribe clinical documentation workflows. Their primary requirement is that immunization events be reported accurately and in a timely manner, typically on the day of administration, after the vaccination has been completed and recorded as final. Depending on system design, this may result in a single VXU containing multiple vaccinations or multiple VXUs each containing a single vaccination event.

Concerns about message volume or transmission efficiency should not drive reporting behavior. HL7 v2 VXU messages are compact, and modern IIS are designed to process them efficiently at scale. Combining multiple vaccinations into a single message does not materially improve processing performance, and submitting systems should prioritize timely, accurate reporting in a form that aligns with their operational workflows.

Sending one VXU per administered vaccination event recorded during an encounter

Sending one VXU containing all vaccinations administered, administered or historical, during an encounter
