"""Generates tooltip entries from the full glossary.

The glossary terms are stored as ### headings in glossary.md.
For each glossary entry, this script takes the first sentence of the definition
and writes it in the format expected by the abbr Markdown extension.

Each variant uses the same tooltip definition as its glossary term.
"""

# Imports

# logging reports problems found while generating the tooltip file
# re is Python's regex module
# unicodedata lets us fold accented letters back to a plain letter
# Path handles the input and output file locations
# here builds file paths from the project root
# date adds the generation date to the tooltip file header

import logging
import re
import unicodedata
from pathlib import Path
from herepath import here
from datetime import date

# Set up the logger
log = logging.getLogger(Path(__file__).stem)

# Get the script name from this Python file for warning messages.
SCRIPT_NAME = Path(__file__).stem

# SETTINGS

# Glossary source file
GLOSSARY_SOURCE = here("mkdocs", "docs", "glossary.md")

# File containing term variants
VARIANT_SOURCE = here("mkdocs", "tools", "outputs", "variant_terms.txt")

# Generated tooltip file
TOOLTIP_OUTPUT = here("mkdocs", "includes", "glossary_tooltips.md")

# Format the generation date for the tooltip file header.
# Format is Sep 27, 2026
generation_date = f"{date.today():%b} {date.today().day}, {date.today().year}"

# Comments added to the top of the generated tooltip file.
HEADER = f"""<!--
Generated: {generation_date}

Glossary behavior for terms listed in this file:
Terms are matched wherever they appear in the handbook.
By default, only the first occurrence of each glossary entry on a page is highlighted.
Terms are not highlighted in headings, table header cells, existing links, or reference footnotes.

Definitions appear as tooltips on hover on desktop.
Format: *[term]: definition
Case variants each need their own line.
Plural variants each need their own line.

The tooltip definition must match the beginning of the full definition in glossary.md.
Do not manually edit this file.
-->"""


# Read the full glossary.
glossary = Path(GLOSSARY_SOURCE).read_text(encoding="utf-8")
glossary_lines = glossary.splitlines()

# Find each glossary term and the first sentence of its definition.
entries = []

for index, line in enumerate(glossary_lines):
    if not line.startswith("### "):
        continue

    term = line.removeprefix("### ").strip()

    # Move past any blank lines after the glossary term.
    next_line = index + 1

    while next_line < len(glossary_lines) and not glossary_lines[next_line].strip():
        next_line += 1

    # Stop if there is no definition before the next heading or end of file.
    if next_line >= len(glossary_lines) or glossary_lines[
        next_line
    ].lstrip().startswith("#"):
        log.warning(
            f"HEY! From: [{SCRIPT_NAME}]. There's a problem. "
            f"Glossary term has no definition: `{term}`"
        )
        log.warning("It must be fixed or no tooltips for you.")
        raise SystemExit(1)

    # Read forward until the first sentence is complete.
    # Stop early as soon as we know more definition text follows it.
    definition_text = ""
    continues = False
    scan_line = next_line

    while scan_line < len(glossary_lines):
        current_line = glossary_lines[scan_line].strip()

        # Stop at the next glossary term.
        if current_line.startswith("### "):
            break

        if current_line:
            definition_text = f"{definition_text} {current_line}".strip()

            definition_parts = re.split(r"(?<=[.!?])\s+", definition_text, maxsplit=1)

            if len(definition_parts) > 1:
                definition = definition_parts[0]
                continues = True
                break

        scan_line += 1

    # If nothing followed the first sentence, the whole definition is the tooltip.
    if not continues:
        definition = definition_text

    entries.append((term, definition, continues))


# Sort glossary entries alphabetically.
# Accented letters are folded to their plain form for sorting.
entries = sorted(
    entries,
    key=lambda entry: (
        unicodedata.normalize("NFKD", entry[0])
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    ),
)


# Read the approved term variants.
# The first item on each line is the canonical glossary term.
# Everything after it is a variant for that term.
variants = {}

for line in Path(VARIANT_SOURCE).read_text(encoding="utf-8").splitlines():
    # Ignore blank lines and comments.
    if not line.strip() or line.lstrip().startswith("#"):
        continue

    parts = [part.strip() for part in line.split("|")]

    canonical_term = parts[0]

    # Stop if the same canonical term appears more than once.
    if canonical_term in variants:
        log.warning(
            f"HEY! From: [{SCRIPT_NAME}]. There's a problem. "
            f"Canonical term appears more than once in [{VARIANT_SOURCE.name}]: "
            f"`{canonical_term}`"
        )
        log.warning("It must be fixed or no tooltips for you.")
        raise SystemExit(1)

    variants[canonical_term] = parts[1:]

# Build the tooltip entries in alphabetical order.
# Each canonical term is followed immediately by its variants.
tooltip_entries = []

for term, definition, continues in entries:
    # Add [...] when more definition text follows the first sentence.
    if continues:
        definition = f"{definition}\u00a0[...]"

    # Add the canonical glossary term.
    tooltip_entries.append(f"*[{term}]: {definition}")

    # Add any variants using the same definition.
    for variant in variants.get(term, []):
        if variant:
            tooltip_entries.append(f"*[{variant}]: {definition}")


# Put a blank line between tooltip entries.
tooltips = "\n\n".join(tooltip_entries)


# Write the header and generated entries to a separate file for review.
Path(TOOLTIP_OUTPUT).write_text(
    HEADER + "\n" + tooltips + "\n",
    encoding="utf-8",
)

print(
    f"HEY! The tooltip generator made {len(tooltip_entries)} tooltip entries "
    f"in {TOOLTIP_OUTPUT.name}. You're welcome."
)
