Patient consent and privacy handling in Immunization Information Systems (IIS) are governed by jurisdictional law. Each state or locality defines whether and how patient data may be included, shared, or withheld from the IIS. Systems must therefore support the ability to record and communicate a patient's explicit consent preferences, while respecting that these indicators have meaning only within the receiving jurisdiction and are not automatically portable across IIS. Consent decisions are often tracked outside HL7 messages.

The HL7 v2.5.1 Protection Indicator (PD1-12) field represents whether a patient or guardian has consented to share or protect their information. The field's name is counterintuitive: a "Y" value means protect (do not share), and "N" means not protected (sharing permitted).

Because consent law varies, PD1-12 is used to record the explicit wishes of the patient or guardian, not to encode system or jurisdiction defaults; submitting systems should omit PD1-12 when consent status is not explicitly collected at the encounter. IIS are responsible for enforcing their own consent rules based on local authority.

Some jurisdictions expect submitters to suppress or flag opt-out patients at the source; others rely on the IIS to enforce opt-out rules. Consent handling may be subject to age-based rules, external consent workflows, or record-locking semantics that are not representable in an HL7 field.

Consent status recorded in PD1-12 affects not only submission but also how the IIS responds to later queries for that patient; see Section 3, Response (RSP) Profiles, for how disclosure restrictions are reflected in query responses.
