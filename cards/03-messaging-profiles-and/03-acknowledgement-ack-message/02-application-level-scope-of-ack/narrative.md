ACK messages defined in this profile apply only to application-level processing outcomes following successful receipt of a VXU by the IIS. They do not represent transport or connectivity behavior and do not substitute for SOAP faults or network-level error handling. IIS receipt of the submitted VXU is a precursor to acknowledgement messaging.

ACK messages communicate the outcome of content validation, patient association, immunization evaluation, and jurisdictional policy application performed by the IIS after the message has reached the application layer.

Transport and connectivity issues prevent a VXU from being submitted to the IIS, or prevent the IIS from returning an ACK in response, and must be investigated and resolved at the transport layer (e.g., per the CDC WSDL) before retrying HL7 v2 messaging. Using an ACK to indicate a transport-layer problem is unreliable and misleading to submitters.

In some architectures, an intermediary supporting data exchange between an IIS and a submitter may need to relay a transport-layer issue originating at the IIS back to the submitter via an ACK. In this scenario, the intermediary should use the enhanced-mode acknowledgement value 'CR' (Commit Reject) rather than 'AR', since 'AR' is reserved for application-level rejection and using it to convey a transport issue would create ambiguity for the submitter.

        1. Transport
        1. Connectivity (e.g., DNS lookup fault, timeout)
        1. Authentication (e.g., TLS authentication failure, invalid credentials/tokens)
        1. SOAP-layer (e.g., unknown operation, invalid SOAP message) Other routing/connectivity issue
