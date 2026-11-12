This section introduces a conceptual data model for immunization information as it is received by an IIS in a VXU message and stored as part of a patient's immunization history. The purpose of this model is to help readers form a clear mental picture of the core data an IIS is designed to manage: patients, their guardians, and the vaccinations associated with them. It is not intended to describe message structure, transport, or system-specific database implementations.

The model represents a minimum shared understanding between trading partners. It highlights the essential concepts that must align across systems for immunization data exchange to work reliably, while intentionally abstracting away from implementation details. Actual IIS implementations are often more complex, for example, storing multiple addresses or address histories, retaining merged or superseded records, or preserving original submissions alongside normalized data. Those details are out of scope here. This model is meant to be useful, not exhaustive.

This data model also intentionally excludes several categories of information. It does not address message construction, authentication, or transmission mechanics (for example, elements conveyed in the MSH segment). It also excludes evaluation and recommendation data returned in response to queries (QBP/RSP), which is transitory in nature and documented separately. The focus here is on persisted clinical and demographic data that forms a longitudinal immunization record.

Within that scope, the model covers two primary areas:

**Patient and guardian information**, including patient identification and classification, registry and consent status, contact details, and limited guardian (parent) identification.

**Vaccination events**, including product identification, administration details, funding information, and key clinical attributes needed to interpret the immunization history.

Other immunization-related concepts, such as refusals, contraindications, immunity evidence, and similar artifacts, are intentionally excluded from this model. These concepts are more variable, less consistently supported across IIS implementations, and are addressed separately in Section 4.8. By narrowing the scope, this section aims to provide a stable conceptual foundation that supports interoperability without attempting to catalog every possible data element an IIS may store.
