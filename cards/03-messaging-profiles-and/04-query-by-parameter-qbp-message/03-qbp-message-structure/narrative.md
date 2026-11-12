The QBP message provides a constrained, IIS-specific use of the HL7 v2 query framework. While HL7 v2 supports a wide range of query patterns, IIS implementations intentionally limit this flexibility to support predictable, synchronous retrieval of immunization information.

For immunization queries, the QBP message is used exclusively to request an immediate response from the IIS. Deferred, batch, or subscription-style query patterns supported in HL7 v2 are not used for IIS interactions.

The core of the IIS query mechanism is the QPD segment, which is customized for immunization use and patterned after patient-identifying fields found in the PID segment. The QPD segment allows the querying system to communicate all known information about a patient to support accurate matching by the IIS.

QBP messages also support optional parameters that influence response behavior, such as requesting a cap on the number of candidate matches returned. These parameters allow querying systems and IIS to coordinate how low-confidence or multiple-possible matches are handled while maintaining predictable performance characteristics.
