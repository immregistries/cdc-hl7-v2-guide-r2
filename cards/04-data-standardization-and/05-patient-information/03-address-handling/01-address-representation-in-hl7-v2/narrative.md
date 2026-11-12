Patient address information is carried in PID-11. HL7 v2 allows multiple address repetitions, each qualified by an address type. IIS must correctly interpret these repetitions rather than relying on positional assumptions that appeared in older guidance.

Addresses associated with contact persons may also appear in NK1 segments. These addresses serve a different purpose and are not a substitute for patient address data.
