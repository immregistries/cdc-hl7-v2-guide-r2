OBX-4 is used to associate related OBX segments that collectively describe a single logical concept. By default, OBX-4 SHOULD be unique for each OBX segment and SHOULD NOT be reused unless the OBX segments are intended to be interpreted together.

Shared OBX-4 values are used in specific, well-defined situations, including:

Linking Vaccine Information Statement (VIS) observations that describe a single VIS event

Grouping related evaluation or recommendation observations that together describe a single evaluation or forecast set

When OBX-4 is used to group observations, the shared value SHALL be unique within the set of OBX segments under a given ORC/RXA and the related OBX segments SHOULD appear sequentially. Systems (including IIS, submitting, and querying systems) SHALL support both grouped and ungrouped OBX-4 usage and SHALL interpret shared OBX-4 values as indicating in a logical association among those OBX segments within the same ORC/RXA group.
