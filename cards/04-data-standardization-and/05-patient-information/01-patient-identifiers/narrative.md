Patient identifiers support ongoing exchange between a submitting system and an Immunization Information System (IIS). They allow the IIS to associate later updates and queries with a previously submitted patient and allow the submitting system to associate an IIS response with its local patient record.

Patient identifiers are issued within an organizational or system context and are not assumed to be globally unique. The same identifier value may refer to different patients when used by different submitting systems or identifier namespaces. IIS commonly segregate submitter identifiers by sending organization, interface, or another locally established namespace.

This section defines the minimum identifier behavior needed for reliable update and query workflows. It addresses the submitter's primary exchange identifier and the IIS registry identifier. It does not define patient-matching algorithms or require IIS to use every identifier included in PID-3.
