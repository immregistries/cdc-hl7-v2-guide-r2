Some changes affect data commonly used by IIS to identify and deduplicate vaccination events. Until source-specific ORC-3 matching is consistently supported, changing one of these fields through a simple update can cause the corrected report to fail to match the earlier report and create a duplicate. A delete followed by an add remains the interoperable correction pattern for these changes.

The identifying fields are RXA-3 Date/Time Start of Administration, RXA-5 Administered Code, RXA-9 Administration Notes (administered/historical indicator), and RXA-11.4 Administered-at Location. RXA-9 is included because it can affect current IIS vaccination matching behavior, not because it identifies the organization that originally reported the vaccination.

This classification determines whether a correction is sent as an update or as a delete followed by an add. It does not define every field that is present in an update or delete message.
