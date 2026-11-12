Beyond special characters, name formatting differences, such as capitalization, spacing, and hyphenation, can affect matching and data quality. IIS should strive to preserve the way a name is submitted while allowing for operational flexibility across systems.

This guide focuses on preserving the submitted name for display and audit, rather than dictating reconciliation or response rules. Systems SHOULD store the submitted name as received. How an IIS matches name variants or chooses which form to return in a query response, is a local policy decision.

"Preserving" refers to keeping the name as submitted, not converting it to all uppercase or changing capitalization patterns. Some IIS currently store all names in uppercase (e.g., SMITH, MCDOWELL), which removes valuable information and can reduce user confidence in record displays.

This guidance promotes clarity and consistency in how names appear within and across systems, improving both matching reliability and end-user trust in displayed patient information.
