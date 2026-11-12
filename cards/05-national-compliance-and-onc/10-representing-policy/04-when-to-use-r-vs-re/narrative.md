A simple heuristic avoids nearly all translation errors:

**Default to RE.** The vast majority of program requirements fall into "Required to Support."

Use R only when the IIS cannot accept the record under any circumstances without the data. If you would still want the vaccination or patient record even when the field is empty, it is RE.

Jurisdictions sometimes tighten RE fields to R because submitting systems fail to properly support RE semantics. This guide recommends enforcing proper RE handling rather than reclassifying fields as R.

Examples where R is appropriate:

Values required for the IIS to safely store or interpret the record (e.g., vaccine code, administration date).

Examples where R is not ideal:

Patient race/ethnicity.

Address

Phone number

Lot number (in most situations).
