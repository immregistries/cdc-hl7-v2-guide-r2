The message-level acknowledgement code (MSA-1) provides a summary of overall disposition. This value is derived from the most severe issue identified within the message. The ACK is constructed from the bottom up: individual ERR segments are evaluated first, and the message-level code is assigned afterward to reflect the highest severity present.

MSA-1 values are:

- AA — Application Accept
- AE — Application Error
- AR — Application Reject

MSA-1 alone does not fully describe the required follow-up for a message; determining the necessary action requires reviewing both MSA-1 and the ERR-4 severities present in the message together.

For population of MSA-1:

- MSA-1 value 'AA':

SHALL NOT be returned when there is an ERR-4 severity 'W' or 'E' error.

- MSA-1 value 'AE':

SHALL NOT be returned when there is an ERR-4 severity 'E' error.

- MSA-1 value 'AR'

SHALL be returned to convey VXU rejection when core intent is not fulfilled; I.e., SHALL be returned when there is an ERR-4 severity 'E' error.

This disambiguates a historical source of confusion, in which 'AE' was sometimes also used to convey rejection, requiring submitters to inspect individual ERR-4 values to determine whether a message had actually been accepted or rejected. Under this profile, 'AE' is reserved exclusively for qualified successful (accepted) transmissions, and 'AR' is reserved exclusively for unsuccessful (rejected) transmissions, so that MSA-1 alone reliably indicates whether resubmission is required.

The presence of an ERR segment in an ACK does not, by itself, indicate that the message was rejected; ERR segments may appear in accepted messages when the issue reported is a Warning or an informational notice.
