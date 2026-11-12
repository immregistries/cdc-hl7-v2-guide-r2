When a query does not result in a single high-confidence match, many IIS support a workflow in which the querying system can assist a user in selecting the correct patient record. From the querying system's perspective, this is not a separate type of query, but a continuation of the original request to identify the correct IIS record.

In these situations, the initial query is evaluated using patient identifying information supplied by the querying system. If the IIS determines that more than one patient record may be a possible match, it may return identifying information for multiple candidate records. This information is intended to support user review and selection, not to establish a permanent linkage.

Once a user selects a candidate record, the querying system re-initiates a standard Z34 or Z44 query using the patient identifying information returned by the IIS for the selected record. At this point, the source of truth for patient identification shifts: the follow-up query relies on the IIS-supplied identifiers and demographics rather than the querying system's original patient information in order to retrieve the specific IIS record selected by the user.

To ensure unambiguous selection, the IIS returns a state registry identifier (SR) for each candidate record. Querying systems are expected to query again with the identifiers and demographics as provided by the IIS for the user-selected patient, including the SR. This allows the IIS to reliably return the intended patient record without re-evaluating the original match criteria.

Selection of a candidate record is inherently transitory. A user's choice reflects a decision to view one specific IIS record at that moment, not a confirmation that the record is the only or definitive match for the patient. Querying systems should not automatically treat this selection as a permanent association between the local patient and the IIS record, as users may intentionally review multiple candidate records when duplicates are suspected.

In limited cases, querying systems may choose to retain the IIS-assigned identifier for future queries. When this approach is used, the system design must make the linkage explicit to the user and provide a clear mechanism to remove or ignore the stored identifier. This ensures that future queries are not constrained to a previously selected record when broader matching is appropriate.

When the user selects a candidate matching record and the querying system re-queries to get a specific patient record:
