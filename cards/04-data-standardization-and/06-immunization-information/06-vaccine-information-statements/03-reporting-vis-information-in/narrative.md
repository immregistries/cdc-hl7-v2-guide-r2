VIS information is reported using one or more OBX segments within the administered vaccination group (ORC/RXA/RXR). IIS may receive two different reporting methods and must support both.

Under the preferred method, submitters report the VIS barcode identifier as an OBX containing the VIS document identifier, followed by a separate OBX giving the date the VIS was provided to the patient. Under the alternate method, submitters report the CVX Unspecified Formulation code representing the applicable VIS, along with an OBX giving the VIS publication date and an OBX giving the VIS date-given. Both methods may appear in the same message, and IIS must be able to accept either approach.

A single administered vaccine may legitimately have multiple associated VIS statements, whether as one combination VIS or as multiple component VISes.

This is especially important for combination vaccines when only individual-component VIS documents are available, so that multiple VIS instances can be unambiguously associated with the single administered CVX product.
