The IIS assigns its own identifier to the consolidated patient record. State IIS represents this identifier using SR. A non-state IIS may use LR. The registry identifier spans the submitting systems that contribute information to the same IIS patient record.

The registry identifier is important in query responses, including responses with multiple possible matches, because it allows a subsequent request to reference the same IIS record. Its presence does not by itself confirm that the requesting system has identified the correct patient.
