This IG defines only the HL7 v2 transactions used for:

Submitting vaccination events (administered and historical) to build complete immunization histories within an IIS jurisdiction.

Querying for consolidated immunization histories and vaccine recommendations.

This guide does not define every HL7 v2 transaction an IIS may use. It excludes Admission/Discharge/Transfer (ADT) messaging, inventory ordering, school or vital records exchange, interstate (IIS-to-IIS) data exchange, transactions specific to the IZ Gateway or other national exchange infrastructure, and federal reporting transactions. ADT and FHIR-based mechanisms are recognized as alternative method of data exchange but are outside the scope of this document. These interactions fall outside the defined scope of IIS update and query workflows.

This guide does not prescribe IIS architecture, internal workflows, or business rules. Each IIS sets its own policies and operational processes. The IG serves as a technical toolbox that supports, rather than dictates, those decisions.

Each IIS SHOULD publish a local implementation guide that defines additional jurisdiction-specific requirements. Not all operational details can be defined at the national level, and some decisions must be made locally. These local guides should be concise, differential documents that build on this national IG, adding or tightening requirements where appropriate rather than restating the entire content. To claim conformance with this national guide, local profiles SHALL NOT introduce any requirements that contradict its normative statements.

Finally, this document represents the collective effort of a broad community-public health professionals, clinicians, system implementers, and standards developers, who have contributed to improving immunization interoperability over more than three decades. Their shared work continues to ensure that accurate, timely, and complete vaccination data help safeguard the health of all people.
