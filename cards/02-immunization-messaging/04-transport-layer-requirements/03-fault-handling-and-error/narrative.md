Transport-level errors are reported using SOAP Faults. Message-level issues are reported in HL7 v2 ACKs.

See the CDC SOAP Transport Specification for the complete definition of each fault type, including its specific parameters (Code, Reason, and Detail) and the corresponding obligations for which systems must be able to throw versus catch each fault.

A positive SOAP response confirms only successful transport, not HL7 v2 message acceptance.
