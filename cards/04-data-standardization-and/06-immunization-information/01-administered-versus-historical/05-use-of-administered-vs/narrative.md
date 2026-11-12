While the administered/historical distinction is meaningful for submission and IIS internal processing, it is not clinically meaningful to querying systems once the IIS has reconciled the patient's record. Querying systems require a complete and accurate vaccination history, not the provenance of each dose.

Historically, IIS have represented this distinction inconsistently in outbound messages. As a result, querying systems cannot reliably interpret or compare administered vs. historical indicators across jurisdictions.

This guide does not define interoperable outbound semantics for the RXA-9 administered/historical indicator. Leaving RXA-9 empty on outbound RSP messages SHOULD be the preferred approach, to avoid implying cross-jurisdictional meaning. IIS that choose to populate RXA-9 MAY do so according to local policy, but such values are not guaranteed to carry the same interpretation in other jurisdictions.
