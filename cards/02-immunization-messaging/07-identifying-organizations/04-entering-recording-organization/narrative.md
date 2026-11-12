Within a responsible organization, vaccinations may be recorded or entered by different organizational units. ORC-17 (Entering Organization) identifies the organization that created or entered the vaccination record. This supports auditing, troubleshooting, and workflow analysis without altering clinical meaning or patient attribution.

ORC-17 identifies an organization but does not require a specific level of organizational hierarchy. Depending on the implementation, the value may represent a clinic, department, facility, or other organizational unit responsible for entering the data. ORC-17 should not be interpreted as a sub-organization of the responsible organization by definition, nor does this guide require that it align with any particular organizational structure.

ORC-17 often overlaps with other organizational identifiers already present in the message, particularly RXA-11.4 for administered vaccinations. For many IIS implementations, these values may be identical, or the ORC-17 value may not currently be used operationally. However, the field remains useful in scenarios such as historical vaccination entry, where the organization recording the data may differ from the organization that administered the vaccine.

Systems typically populate ORC-17 with the organization that entered or recorded the vaccination, and IIS often retain these values for auditing and analysis. Because operational use of ORC-17 varies across implementations, IIS generally do not treat the field as a condition for message acceptance.

The usage of ORC-17 may be evaluated in future revision of this implementation guide if real-world adoption remains limited.
