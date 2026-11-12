Earlier versions of the National IG defined separate query profiles to support closely related use cases: one to retrieve a patient's immunization history, and another to retrieve that same history with clinical evaluation and forecast. Although these profiles were intended to serve distinct purposes, they shared nearly identical structure and requirements, and the practical distinction between them was often unclear to implementers.

In real-world implementations, IIS and querying systems treated these profiles as variations of the same interaction. Subtle structural and conformance differences were not consistently implemented or enforced, leading to unnecessary complexity without corresponding benefit. This guide formalizes what has become common practice by harmonizing the profiles.

Under this unified model, both profiles request the same underlying data: the complete immunization history consolidated by the IIS for a patient. The only functional distinction is whether the querying system is explicitly requesting that the IIS include evaluation and forecast results in the response.

The Z34 profile ("Request a Complete Immunization History") is used to retrieve a patient's full immunization history. Evaluation and forecast information may be included in the response but are not required. The Z44 profile ("Request Evaluated Immunization History and Forecast") is used when the querying system requires evaluation and forecast results.

Both profiles allow evaluation and forecast to be returned, and querying systems may receive these results in either response. Querying systems are expected to safely ignore evaluation and forecast content when it is not needed for their use case.

Some current IIS implementations return different content for Z34 and Z44; this guide intentionally aligns expected behavior going forward. Implementers should validate local behavior and perform interoperability testing before relying on the unified model in production.
