This Implementation Guide is authored and published using a model that tightly couples documented requirements with validation and testing. Earlier versions of the guide were published primarily as narrative documents, with computable message constraints derived later for use in testing tools. That approach proved error-prone and difficult to maintain. This release is built directly from structured requirements authored in the Immunization Guide Authoring Management Tool (IGAMT) [1], ensuring that what is documented and what is tested are consistent by design. At the core of the guide is the Message Infrastructure section, which defines the computable message formats used for validation. The surrounding narrative sections are intentionally organized to explain, justify, and support those requirements. As a result, the guide can be published in multiple formats and incorporated directly into current and future tooling without re-interpretation.

**1. Overview and Introduction**

This section establishes the purpose, scope, and intent of the guide. It introduces key objectives, shared terminology, and the conformance language used throughout. The goal is to align expectations early so readers understand how requirements are expressed and how the document should be read.

**2. Immunization Messaging Fundamentals**

This section provides the conceptual and operational foundation for the guide. It explains the use of HL7 v2 in the context of public-health immunization systems, including how data flows, how acknowledgements are processed, and why data quality processes are essential for IIS. It also introduces core concepts that may be assumed knowledge for experienced implementers but are critical context for readers new to IIS or HL7.

**3. Messaging Profiles and Transactions**

This section defines the set of message types and transactions supported by the guide and how they relate to common immunization use cases. It establishes the scope of message exchange covered, including updates, queries, responses, and acknowledgements, and how these interactions fit together as a coherent messaging model.

**4. Data Standardization and Integration**

This section provides topic-focused guidance on how immunization data should be represented and exchanged in real systems. It addresses recurring implementation questions and edge cases based on operational experience, explaining the rationale and practical handling of specific data elements. These sections focus on the "why," "what," and "how" of data exchange and are intended to be read in conjunction with the formal message requirements defined in 7. Message Infrastructure.

**5. National Compliance and ONC Regulations**

This section explains how the guide supports national conformance, validation, and regulatory requirements. It describes how local implementation guidance relates back to the national standard, how policy requirements may be represented in HL7 v2, and how this guide aligns with broader certification and compliance activities.

**6. Preparing for Version Updates**

This section describes how the guide evolves over time. It explains the relationship between versions, Technical Advisory Bulletins, and future updates, with the intent of balancing stability for implementers with the need to incorporate improved approaches as standards and practices mature.

**7. Message Infrastructure**

This section contains the complete, structured definition of message profiles and requirements, including message structures, segments, fields, data types, and coded values. It represents the computable core of the guide and supports automated validation and testing, including NIST tooling.

Unlike the narrative chapters that preceded it, this section is not intended to be read sequentially. It functions as a reference, consulted as needed for specific information such as data types or value sets, rather than material to be read start to finish. While this section defines all machine-testable requirements, it does not replace narrative requirements elsewhere in the guide, which remain equally binding even when they cannot be automatically validated.

**8. Appendix A: Example Messages**

This appendix provides example messages that illustrate correct use of the standard. The examples are conformant with the defined message rules and are intended to support understanding and implementation. Readers should use these examples in combination with the narrative guidance and message infrastructure to ensure correct and complete implementation.

**9. Appendix B: Glossary and Abbreviations**

This appendix defines key terms and abbreviations used throughout the guide to promote consistent understanding.

**10. Appendix C: List of Figures and Diagrams**

This appendix provides a numbered list of all figures, tables, and diagrams referenced throughout the guide, along with the section in which each appears, to help readers quickly locate specific visual content.

**11. Appendix D: Immunization and Public Health Data Exchange Resources**

This appendix provides references and links to external resources relevant to immunization and public-health data exchange.

**11. Change History**

This section documents changes made between releases of the guide, allowing readers to track updates and understand how requirements have evolved over time.
