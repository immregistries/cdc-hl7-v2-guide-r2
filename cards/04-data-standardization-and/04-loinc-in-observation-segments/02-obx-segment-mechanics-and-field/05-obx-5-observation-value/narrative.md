OBX-5 carries the value of the observation and represents the "answer" to the question defined by OBX-3. The expected format and allowable value sets for OBX-5 are determined by the data type in OBX-2 and the constraints shown in the tables in this section.

Systems SHOULD NOT send OBX segments without a populated OBX-5 value, since an OBX without OBX-5 conveys no meaningful information and is discouraged. Empty OBX-5 values are occasionally observed in production interfaces, however, and while not ideal, IIS may interpret an empty OBX-5 as indicating that no observation is present.
