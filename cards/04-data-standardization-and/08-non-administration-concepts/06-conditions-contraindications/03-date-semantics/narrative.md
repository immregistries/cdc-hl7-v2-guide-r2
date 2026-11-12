OBX-14 represents the date the observation was authored or recorded. It does not indicate when the underlying condition began, except for ongoing conditions such as pregnancy or allergies, where the onset date/time is used. The effective and expiration date OBXs are the only elements that convey temporal applicability of the condition itself.

Implementers should not assume alignment between OBX-14 and the onset of the condition.

Relationship to Non-Administered Doses

Conditions may be sent either:

As standalone patient-level observations, or

Within an ORC/RXA group where RXA-20 indicates that a vaccine was not administered

From an IIS perspective, these are processed identically. The condition is treated as a patient-level observation regardless of whether the RXA references CVX 998 ("No vaccine administered") or a specific vaccine CVX.

The presence of RXA-20 = NA establishes only that no vaccination occurred. It does not create standardized meaning linking the condition to a specific non-administered vaccine. IIS should not infer whether the condition applies to one vaccine, a class of vaccines, or vaccination in general.

RXA dates and vaccine identifiers in this context do not carry clinical meaning and must not be interpreted as vaccination events. Submitting systems may populate required RXA fields to satisfy HL7 syntax; receiving IIS should not validate or act on those values beyond recognizing that no vaccine was administered.
