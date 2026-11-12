Immunization messaging relies on multiple code systems because vaccine information is used for different operational purposes, including clinical history, product traceability, and legacy billing workflows. IIS and submitting systems are expected to recognize these code systems and apply them appropriately without conflating their roles.

In HL7 v2 immunization messaging, CVX is the canonical representation of the vaccine administered or historically received. NDC provides product-level detail for administered doses and supports traceability. CPT may appear in legacy interfaces but is no longer preferred and should be avoided for routine immunization reporting.

**Vaccines Administered Code (CVX)**: The CDC-maintained code system used to represent what vaccination the patient received and the canonical vocabulary for IIS immunization history, evaluation, and forecasting.

**National Drug Code (NDC)**: An FDA-maintained code system used to identify specific manufactured vaccine products and packaging, primarily for inventory management, lot tracking, and traceability of administered doses.

**Current Procedural Terminology (CPT)**: A billing-oriented procedure code system historically used by legacy systems to report vaccination activity, now discouraged and retained only to support older interfaces that have not yet transitioned to CVX and NDC.
