Organization identifiers throughout this guide, including MSH-4, MSH-22, ORC-17, and RXA-11.4, rely on HL7 v2 data types that support multiple identifier components. In current practice, however, most IIS implementations populate only the primary identifier component of these data types rather than the full underlying structure. To reduce ambiguity while remaining compatible with existing interfaces, this section defines a standardized, simplified data-type profile for organization identifiers.

This profile is based on the HL7 v2 HD (Hierarchic Designator) data type. Within this structure, the primary identifier component, HD.1, carries the IIS-defined organization identifier. Other components of the HD data type remain optional and may be populated when supported by local implementations, but are not required to convey the organization identifier itself.

This representation applies consistently across the key organization identification fields used in immunization messaging:

- MSH-4 (Submitting Organization)
- MSH-22 (Responsible Organization)
- RXA-11.4 (Administering Organization)

This simplified structure reflects current operational practice across IIS implementations rather than introducing a new requirement. It is not intended to preclude future use of additional data-type components to support nationally recognized identifiers, such as the National Provider Identifier (NPI), OID-based identifiers, or provider-directory identifiers. Systems that wish to represent these identifiers in the future may do so using additional components of the HD data type, without requiring immediate changes to existing implementations.

Standardizing this profile now improves interoperability clarity across jurisdictions while preserving forward compatibility for more detailed identifier models as they mature.
