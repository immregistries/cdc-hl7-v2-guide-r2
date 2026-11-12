Each ERR-4 severity maps to a combination of three actions:

- **Convey**- communicate the issue to the appropriate user or audience in an understandable, actionable form, both in the context of the specific transaction and in aggregate.
- **Correct**- address the issue at its source, which may mean correcting the underlying patient or immunization record, or improving an upstream workflow, and does not necessarily require a revised message.
- **Resubmit**- send an updated, corrected message to the IIS, required only when core intent was not fulfilled.

These actions are cumulative and hierarchical: each higher-severity action includes the responsibilities of the lower ones. They apply to the individual issue described in a given ERR segment; the overall message disposition is calculated separately, based on the most severe issue present in the message, and reflected in MSA-1.

Each ERR segment with a severity of Warning or Error SHALL be conveyed to appropriate users by the submitting system, not as raw HL7 v2, but as structured, understandable information (for example, as individual rows in a user interface, a report, or a workflow-integrated feedback view), drawing on ERR-2, ERR-4, ERR-5, and ERR-8 to support the required follow-up action.

Resubmission is not merely a retransmission of the original data; it is the result of identifying and correcting the underlying issue, regardless of where it originated, so that the IIS receives a complete and accurate submission. Resubmitting the same message without correction is not appropriate and can overload IIS systems. Because an ACK does not distinguish between sender-side and receiver-side faults, any message requiring resubmission signals that at least one system, on either or both sides, must investigate and resolve the issue before the corrected message is resent.
