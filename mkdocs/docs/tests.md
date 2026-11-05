# Behavior Tests & Edge Cases

This page lists behavior tests and edge cases for the glossary.

1. Add a test for term variants. Checks that all variants of the same glossary term share one count per page, controlled by the `MARKS_PER_PAGE` setting in `glossary_links.py`. At the **default of 1**:  
The first accelerators is underlined, but the later Accelerator is not.

2. Add a test for links between glossary definitions. Checks that only the first occurrence of each related term is linked within a definition, with counts reset for each new definition by `MARKS_PER_DEFINITION`.  
Use Training set, Validation set, and Test set. Each definition should link to the other two once.

3. Add a test for a manual term exception: epochs.

4. Add a test for Objective & key results. Checks that an ampersand is handled correctly in the glossary link.

5. Add a test for AI/ML workflow. The slash should be removed from the heading ID rather than turned into a hyphen.

6. Add a test for auditable infrastructure. Checks that a glossary definition can contain bullets.

7. Add a test for overlapping glossary terms. Checks that a longer glossary term and the shorter term contained within it are matched as separate entries.  
Real-time inference and Inference, or Deployment plan and Deployment

8. Add a test comparing a one-line definition with a multi-line definition. Checks that the tooltip for the multi-line definition includes `[...]`.  
Use Explainability for the one-line definition and Benchmarking for the multi-line definition.

9. Add an **exclusion** test. Confirm that a glossary term inside an existing hyperlink stays a normal link instead of being turned into a glossary link.  
Link to my favourite: [ARX For Fun And Profit](https://youtu.be/QDia3e12czc)

10. Add an **exclusion** test for a glossary term in a table column header. No glossary links in column headers.

    | Challenge | Feature encoding should not be a glossary term here. | Neither should Container. |
    | --- | --- | --- |
    | Exciting content. | More exciting content. | spaCy can have a link. |

11. Add an **exclusion** test for glossary headings and self-links. Headings should stay unlinked. In Data management plan, its own name should stay plain text. In DVC, the software name should link to its external website, not the Data version control glossary entry.

12. Add an **exclusion** test for reference footnotes. Checks that glossary terms in reference footnotes receive neither tooltips nor glossary links.  
Let's add two references here.[@gebruDatasheetsDatasets2021; @mitchellModelCardsModel2019]  
