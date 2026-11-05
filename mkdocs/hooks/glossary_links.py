"""Links glossary terms in MkDocs handbook pages to Ionic Explorer cards.

The abbr extension wraps matching terms in <abbr title="...">.
After each handbook page is rendered, this hook links the first eligible
occurrence of each glossary term to its card while preserving the tooltip.

Headings, table header cells, existing links, and reference footnotes are
excluded. Glossary definition links are generated separately in JSON.
"""

# Imports

# logging sends the warnings to MkDocs so they show up coloured
# re is Python's regex module
# unescape turns things like &amp; back into normal characters
# Path lets us get the hook name from this Python file
# here builds file paths from the project root
# markdown_slugify creates the same anchor IDs used by the Ionic cards
# get_relative_url works out the path from a handbook page to the Explorer

import logging
import re
from html import unescape
from pathlib import Path
from herepath import here
from markdown.extensions.toc import slugify as markdown_slugify
from mkdocs.utils import get_relative_url

# Get the hook name from this Python file for warning messages.
HOOK_NAME = Path(__file__).stem

# Set up the logger
# The name has to start with mkdocs. so MkDocs formats the warnings
# hooks says what this file actually is

log = logging.getLogger(f"mkdocs.hooks.{__name__}")

# SETTINGS

# Glossary Explorer URL within the combined published site.
# Example: a handbook reference to Fairness goes to glossary/#fairness.
# The Vite build must be published at this location for links to work.
GLOSSARY_URL = "glossary/"

# Glossary source file
GLOSSARY_SOURCE = here("mkdocs", "docs", "glossary.md")

# How many times each glossary term is marked on a page

# Variants of the same term share one count, so Fairness and fairness count as one term
# 0 marks every Fairness and every fairness on the page
# 1 marks whichever of them comes first and leaves the rest plain (default)
# 2 marks the first two of them, and so on

# This is the variable you change:

MARKS_PER_PAGE = 1

# Terms already warned about during this build, so each problem is only reported once.
seen = set()


# Clear warning history at the start of each build.
def on_pre_build(config):
    seen.clear()


# Regex patterns for finding terms in the rendered HTML

# Find glossary terms that Markdown has wrapped in <abbr> tags.
# Capture the tooltip text separately from the visible term text.
ABBR = re.compile(r'<abbr title="([^"]*)">(.*?)</abbr>', re.DOTALL)

# Find HTML areas where glossary behavior should be removed:
# headings, table header cells, existing links, and reference footnotes.
EXCLUDED = re.compile(
    r'(<h[1-6][^>]*>.*?</h[1-6]>|<th[^>]*>.*?</th>|<a\b[^>]*>.*?</a>|<div class="footnote">.*?</div>)',
    re.DOTALL,
)


# Turn a canonical glossary term into its corresponding Ionic card anchor.
def slugify(term):
    return markdown_slugify(unescape(term), "-")


# GLOSSARY LOOKUP

# Read glossary headings and definitions to resolve terms on handbook pages.
# Each glossary term must be a ### heading, followed by its full definition.
def read_glossary_entries():

    with open(GLOSSARY_SOURCE, encoding="utf-8") as f:
        glossary = f.read()

    return re.findall(
        r"^###\s+(.+?)\s*$\n+\s*(.+)$", glossary, re.MULTILINE
    )


# Match the short tooltip definition to the full glossary definition.
# Variants use the same definition, so they resolve to the same canonical heading.
# Report missing and ambiguous matches through the existing MkDocs warnings.
def find_glossary_heading(title, term, glossary_entries):

    # Remove the continuation marker only when matching to the glossary definition.
    match_title = title.removesuffix("\u00a0[...]")

    # The tooltip text must match the beginning of the glossary definition,
    # and the matching heading is used as the link destination.
    matches = [
        heading.strip()
        for heading, definition in glossary_entries
        if definition.strip().startswith(match_title)
    ]

    # Warn if the tooltip definition matches more than one glossary entry.
    # An ambiguous match cannot be linked reliably.
    # Report the conflicting glossary entries together and only once.

    if len(matches) > 1:
        warning_key = ("ambiguous", tuple(matches))

        if warning_key not in seen:
            seen.add(warning_key)
            log.warning(
                f"HEY! From: [{HOOK_NAME}]. There's a problem. "
                f"More than one glossary entry shares a definition: "
                + ", ".join(f"`{heading}`" for heading in matches)
            )

        return None

    heading = matches[0] if matches else None

    # Warn if the tooltip definition does not match an entry in glossary.md.
    # Warn once per term so a repeated term does not flood the output.
    # Leave the term as a tooltip without a link so the site can still build.

    if heading is None:
        if term not in seen:
            seen.add(term)
            log.warning(
                f"HEY! From: [{HOOK_NAME}]. There's a problem. "
                f"The tooltip definition for `{term}` does not match any glossary definition."
            )

    return heading


# Remove glossary markup from excluded elements, leaving the text as written.
def strip_abbr(match):
    return match.group(2)


# Run after MkDocs renders each handbook page.
def on_page_content(html, page, config, files, **kwargs):

    # How many times each glossary entry has been marked on this page.

    marked = {}

    # Work out the relative path from the handbook page to the Ionic Explorer.

    target = get_relative_url(GLOSSARY_URL, page.url)

    # Read glossary headings and definitions.
    glossary_entries = read_glossary_entries()

    # Replace each glossary tooltip with a link.
    # Flow: tooltip text → compare against full glossary definitions → find the matching glossary heading
    # → build the link to that heading

    def replace(match):

        # Get the tooltip definition and the term as it appears on the page.
        title, term = match.group(1), match.group(2)

        # Resolve the term to its canonical glossary heading.
        heading = find_glossary_heading(title, term, glossary_entries)
        if heading is None:
            return f'<abbr title="{title}">{term}</abbr>'

        # Count this occurrence against the entry's budget for this page.

        marked[heading] = marked.get(heading, 0) + 1

        # Leave later occurrences as plain text, with no underline and no link.

        if MARKS_PER_PAGE and marked[heading] > MARKS_PER_PAGE:
            return term

        # Keep the <abbr> element for tooltip styling, but wrap it in
        # a link to the matching Ionic glossary card.

        # A keyboard accessibility issue: 
        # While navigating handbook pages via Tab, glossary links receive focus, but tooltips do not appear.
        # In Microsoft Edge, moving the title attribute onto the link caused overlapping
        # native Edge and Material tooltips. This issue is not easily resolved.
        # Keyboard users can still follow links to the full glossary definitions.
        # A similar issue was documented in Bootstrap (2015):
        # https://github.com/twbs/bootstrap/issues/18692

        return (
            f'<a class="glossary-link" href="{target}#{slugify(heading)}">'
            f'<abbr title="{title}">{term}</abbr></a>'
        )

    # Remove glossary markup from headings, table headers, reference footnotes, and existing links.
    # These occurrences do not count toward the per-page marking limit.
    # EXCLUDED.split() keeps the excluded HTML blocks in the list.
    # Even-numbered parts are normal content; odd-numbered parts are excluded areas.
    # Normal content gets glossary links; excluded areas only have the <abbr> markup removed.

    parts = EXCLUDED.split(html)
    output = []

    for i, part in enumerate(parts):
        if i % 2:
            # Remove glossary markup from excluded areas, leaving the text as written.
            output.append(ABBR.sub(strip_abbr, part))
        else:
            # Add glossary links to normal content, using the per-page marking limit.
            output.append(ABBR.sub(replace, part))

    return "".join(output)
