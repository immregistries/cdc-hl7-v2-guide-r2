A programmatic requirement describes an expectation for how providers document, store, or support data in their systems and workflows.

An HL7 conformance requirement describes what must appear in the message structure to ensure the IIS can parse, understand, and safely accept the transaction.

These two domains intersect but are not interchangeable. Most programmatic requirements map to RE (Required but may be empty), not R (Required and must appear). RE is not optional. It means the sending system must support capturing and transmitting the data when known and must be testable at certification time.

- If a program requirement says "must collect it," that is RE, not R.
- If a program requirement says "you cannot submit this record without it," that is R.

Misusing R to enforce program expectations is a category error. HL7 conformance constraints operate only at message acceptance and certification. Program compliance happens through training, onboarding, monitoring, and follow-up, not through message structure.
