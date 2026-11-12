Mislabeling fields as R produces three predictable failures:

**Bogus data creation.** When systems must populate fields they cannot truly support, engineers respond by generating default values. IIS then receives data that looks complete but is false, misleading, or harmful for matching and analytics.

**Provider suppression of legitimate events.** When a Required field is absent, some systems simply suppress the entire vaccination rather than transmit incomplete data. IIS loses real administered doses.

**Non-standard behavior.** IIS diverge from national expectations, creating expensive onboarding burdens and eroding trust in the guide.

These outcomes actively undermine policy goals: A clear example is patient address. Clinical systems usually collect addresses, but there are legitimate situations where an address is unknown, unverified, or not applicable, for example, patients who are between residences or experiencing homelessness. When an IIS marks address as Required (R), submitters are forced into two bad choices: suppress the vaccination entirely or insert fabricated values ("no address," "homeless," placeholder ZIP codes). Both violate national expectations for complete reporting and inject bad data that complicates patient matching, distorts completeness metrics, and undermines outreach efforts. Mislabeling an RE field as R does not improve compliance- it causes data loss and data corruption.
