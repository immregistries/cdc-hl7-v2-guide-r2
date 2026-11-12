OBX-1 contains the sequence number of the OBX segment within the message. Two numbering patterns are commonly observed in production systems:

Global sequencing, where OBX-1 starts at 1 for the first OBX in the message and increments across all Order Segment Groups.

Per-Order Segment Group sequencing, where OBX-1 restarts at 1 within each ORC/RXA group.

OBX-1 is not used to convey clinical meaning and does not affect how observations are grouped or interpreted. Systems (including IIS and querying systems) SHALL accept messages that use either global sequencing or per-order-segment-group sequencing for OBX-1, and SHALL NOT rely on OBX-1 for semantic processing.
