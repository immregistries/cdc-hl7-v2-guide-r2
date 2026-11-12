Names play a central role in matching patient records, but they are not fixed identifiers. Across the health ecosystem, names may differ slightly between systems due to nicknames, abbreviations, character encoding, or updates from other data sources. IIS receive information from many contributors and aim to maintain the most accurate and up-to-date version of each patient's name that they can determine from those inputs.

The goal of this guidance is to encourage consistency while recognizing that perfect alignment is not always possible. IIS and submitting systems must be designed to tolerate reasonable variation and to use names as matching elements, not as absolute keys.

Querying systems SHOULD NOT expect the IIS to return exactly the same name string that was previously submitted. Returned names may reflect updated or corrected data from other sources.

These expectations reinforce that IIS are not the source of truth for patient names. Instead, they serve as aggregators of data from many systems, maintaining linkages even as individual name representations evolve. The shared objective is for all systems to transmit and interpret the best available representation of each patient's name: accurate enough for matching, flexible enough for interoperability.
