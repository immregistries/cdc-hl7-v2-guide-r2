HL7 v2.5.1 defines OBX-14 as the physiologically relevant date/time, or the closest approximation to that date/time, for the associated observation. A few basic principles govern how OBX-14 should be populated.

In general, the OBX-14 date/time should reflect when the observation itself occurred or was recorded. For observations that span multiple days, such as pregnancies or allergies, the onset date/time should be used. For serology-based observations, such as serological immunity, the date/time the blood was drawn should be used.

General Observation, Indication, and Contraindication observations are associated with related codes for effective and abatement dates. Because the relevant date for these coded observations is carried in a related OBX segment, OBX-14 need not be populated in the primary OBX segment; for example, a Contraindication OBX segment does not need OBX-14 populated so long as it is accompanied by a Contraindication Effective Date OBX segment. Neither onset nor abatement date observations have a relevant date/time of their own, so OBX-14 need not be populated for those either.

If the appropriate value is not known, OBX-14 should remain empty; it is an RE field and is not required in every message instance. If the observation date is unknown or cannot be represented accurately, OBX-14 SHALL be omitted.

RXA-3 and OBX-14 will not always carry the same date/time, since the relationship between them depends on the type of observation being reported:

- Patient-level observations, such as Serological Immunity, History of Disease Immunity, and Reaction (when it cannot be attributed to a specific administration event), follow an RXA segment where RXA-3 reflects the date/time the report is being made, that is, when the message is constructed.
- Administration event-level observations, including evaluation-related observations in an RSP message (Eligibility, Funding Source, VIS Related, Reaction when attributable to a specific administration event, Comment, and Evaluation Related), follow an RXA segment where RXA-3 reflects the date/time the vaccine was administered, even if the report is submitted later, such as when an adverse reaction is reported several days after administration.
- Forecast-level observations follow an RXA segment where RXA-3 reflects the date/time the evaluation and forecast were performed, which is typically very close to when the message is constructed.
- RSP messages echo the date/time a submitter sent in the corresponding VXU message.
