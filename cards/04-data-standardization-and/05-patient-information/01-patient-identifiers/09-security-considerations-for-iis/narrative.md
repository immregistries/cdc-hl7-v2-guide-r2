An SR or LR identifies an IIS patient record, but it is not an authentication credential or independent proof of patient identity. Registry identifiers that are sequential, predictable, or otherwise easy to guess may be subject to enumeration, in which repeated identifier values are used to attempt to retrieve patient records.

IIS should reduce the predictability of registry identifiers shared outside the IIS when practical. Regardless of identifier format, an IIS must not disclose a patient record based solely on the presence of a valid SR or LR. Query processing must also evaluate demographic information and apply appropriate authentication, authorization, monitoring, rate-limiting, and other protections.

Additional guidance on protecting IIS interfaces from identifier enumeration and related threats is provided in AIRA’s *Security Guidance Considerations for Immunization Information Systems* [7].
