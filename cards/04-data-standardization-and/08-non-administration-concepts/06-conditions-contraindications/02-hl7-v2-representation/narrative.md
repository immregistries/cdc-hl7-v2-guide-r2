Patient-level conditions are reported as observations using a single ORC/RXA group that explicitly indicates that no vaccination event is being reported. This ORC/RXA group functions solely as a container for OBX segments conveying clinical meaning.

On the wire, conditions are expressed using existing vaccination contraindication/precaution LOINC codes, even though the clinical concept being conveyed is broader than a simple contraindication.

The following LOINC codes are used:

30945-0 - Vaccination contraindication/precaution

REQUIRED to convey the condition itself

30946-8 - Vaccination contraindication/precaution effective date

OPTIONAL

Indicates when the condition became applicable

30944-3 - Vaccination temporary contraindication/precaution expiration date

OPTIONAL

Indicates when a temporary condition is no longer applicable
