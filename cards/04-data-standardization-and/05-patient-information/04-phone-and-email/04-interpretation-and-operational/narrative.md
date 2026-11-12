Distinguishing cellular from landline numbers based solely on HL7 v2 message content is unreliable. Numbers designated as "telephone" are frequently mobile phones, and equipment type values are often miscoded or outdated. As a result, IIS should not rely on XTN content to determine SMS capability.

Given current usage patterns in the United States, IIS should assume that submitted phone numbers are cellular unless validated otherwise. When precise determination is required, for example, to support text messaging, external validation services provide a more reliable approach.

Legacy contact methods such as fax, pager, or TDD are not expected in modern IIS submissions and do not require special handling.
