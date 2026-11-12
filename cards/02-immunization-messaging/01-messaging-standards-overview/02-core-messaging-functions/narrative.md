The HL7 v2.5.1 immunization standard supports two primary interactions:

Update (VXU): Used by submitting systems to report new, modified, or deleted immunization events to the IIS. The IIS responds with an Acknowledgement (ACK) message indicating if the patient and vaccination information was accepted and additional information about any data quality problems found that need to be addressed.

Query (QBP): Used by querying systems to request complete immunization histories and recommendations. The IIS responds with a Response (RSP) message containing patient records and forecasts, if available.

These messages support clinical workflows, enabling systems to send and retrieve immunization data efficiently to inform care decisions.
