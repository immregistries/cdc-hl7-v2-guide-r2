HL7 v2 messages are composed of:

Segments (e.g., MSH, PID, RXA, OBX): Represent lines in the message, each with a defined structure.

Fields: Separated by the pipe (|) character, representing data elements within each segment.

Components and Subcomponents: Separated by ^ and &, used for complex field values.

Repeat Fields: Separated by ~ when multiple values are present.

The guide defines message profiles that constrain these structures for immunization-specific use, specifying which segments, fields, and values are required, optional, or conditionally required.
