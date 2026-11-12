Immunization messaging relies heavily on coded values to convey clinical meaning, administrative intent, and demographic context. These coded values are not uniform in how they change over time or how strictly they must be constrained. Some code sets evolve frequently and require active monitoring, while others are intentionally static to preserve stable processing behavior across systems.

Misunderstanding the nature of a code set, whether it is dynamic or static, open or closed, can lead to brittle implementations, unnecessary message rejections, or silent data corruption. Systems that treat all code sets the same way risk either over-constraining data that should be flexible or under-validating data that is foundational to correct immunization processing.

This section describes how value sets are classified along two independent dimensions, stability (dynamic vs. static) and extensibility (open vs. closed), and explains the expectations IIS and submitting systems must meet for each category. See Section 7.4 for Value Sets and authoritative lists and field-level assignments.

**Dynamic**: A code set whose contents are expected to change regularly and therefore require active monitoring, versioning, and notification of changes.

**Static**: A code set intended to remain stable over time; changes are rare and typically governed at the national level.

**Open**: A code set that permits jurisdictional or local extensions.

**Closed**: A code set that does not permit local extensions; only canonical values are accepted.

Together, these two dimensions define four operational categories, each with distinct expectations for IIS and submitting systems. A static-closed code set requires strict validation, where unknown values are treated as errors unless the code set is formally updated through the national process. A static-open code set maintains a stable baseline of values while allowing local extensions; IIS must publish any local extensions and notify partners when they are introduced. A dynamic-closed code set changes over time but does not permit local extensions, requiring systems to support versioning and apply updates in a timely manner. A dynamic-open code set combines frequent change with allowed local extensions, and therefore requires the most active governance, including machine-readable publication of changes and ongoing coordination with partners.
