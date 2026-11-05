"""Generate JSON data for the Ionic Glossary Explorer cards.

Reads canonical terms and definitions from glossary.md and uses glossary
variants to identify where terms appear across the eight AI lifecycle chapters.
Terms not found automatically can receive one or more manual stage assignments.

Reads parent–child and peer relationships from the spreadsheet, validates
them against canonical glossary terms, and assigns the appropriate display
labels to both connected terms. Reads their display order from the Labels
worksheet, so the glossary cards can show closer relationships first.

Adds definition links only when the pair has no curated relationship.
Exports glossary.json and a detailed text report to vite/tools/outputs/.
"""

# Imports

# json writes the glossary data in a format the website can read
# date records the local date when the JSON file is generated
# re finds glossary terms, protects existing Markdown, and builds URL anchors
# unicodedata keeps Python link anchors consistent with the Ionic cards
# Path reads and writes text files and creates the output folder
# here builds project-relative file paths
# load_workbook reads the relationship spreadsheet without changing it

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from herepath import here
from openpyxl import load_workbook


# SETTINGS

# All input and output files are defined here so they can be changed in one place.

GLOSSARY_SOURCE = Path(here("mkdocs", "docs", "glossary.md"))
VARIANTS_SOURCE = Path(here("mkdocs", "tools", "outputs", "variant_terms.txt"))
MANUAL_STAGES_SOURCE = Path(here("vite", "tools", "inputs", "manual_stages.txt"))
RELATIONSHIPS_SOURCE = Path(here("vite", "tools", "inputs", "term_relationships.xlsx"))
RELATIONSHIPS_SHEET = "term_relationships"
LABELS_SHEET = "Labels"
OUTPUT_FILE = Path(here("vite", "tools", "outputs", "glossary.json"))
REPORT_FILE = Path(here("vite", "tools", "outputs", "glossary_report.txt"))

# Within each definition, link a term only on its first eligible occurrence.
# Set to 0 to link every eligible occurrence.
MARKS_PER_DEFINITION = 1

# Chapter order matches mkdocs.yaml. Keep IDs stable if the stage names change.
# Each chapter's file path is specified here rather than inside the processing code.

LIFECYCLE_STAGES = [
    ("id_1", "Problem Definition & Planning", Path(here("mkdocs", "docs", "problem-definition.md"))),
    ("id_2", "Data Preparation", Path(here("mkdocs", "docs", "data-preparation.md"))),
    ("id_3", "Model Selection & Development", Path(here("mkdocs", "docs", "model-selection.md"))),
    ("id_4", "Model Training & Tuning", Path(here("mkdocs", "docs", "model-training.md"))),
    ("id_5", "Benchmarking, QC & Optimization", Path(here("mkdocs", "docs", "benchmarking.md"))),
    ("id_6", "Model Application", Path(here("mkdocs", "docs", "model-application.md"))),
    ("id_7", "Results & Reporting", Path(here("mkdocs", "docs", "results-reporting.md"))),
    ("id_8", "Cross-Cutting Considerations", Path(here("mkdocs", "docs", "cross-cutting.md"))),
]


# READ THE GLOSSARY

glossary_text = GLOSSARY_SOURCE.read_text(encoding="utf-8")

headings = list(re.finditer(r"^### (.+)$", glossary_text, re.MULTILINE))

glossary_entries = []

for index, heading in enumerate(headings):
    term = heading.group(1).strip()

    definition_start = heading.end()
    definition_end = (
        headings[index + 1].start()
        if index + 1 < len(headings)
        else len(glossary_text)
    )

    definition = glossary_text[definition_start:definition_end].strip()

    glossary_entries.append({
        "term": term,
        "definition": definition,
    })


# READ CANONICAL TERMS AND VARIANTS

# Each canonical term is always searchable, even if it has no variants.
search_forms = {
    entry["term"]: {entry["term"]}
    for entry in glossary_entries
}

for line_number, line in enumerate(VARIANTS_SOURCE.read_text(encoding="utf-8").splitlines(), start=1):
    if not line.strip() or line.lstrip().startswith("#"):
        continue

    parts = [part.strip() for part in line.split("|")]
    canonical_term = parts[0]

    if canonical_term not in search_forms:
        print(
            f"HEY! Unknown term `{canonical_term}` on line {line_number} "
            f"of {VARIANTS_SOURCE.name}. No matching canonical term exists in {GLOSSARY_SOURCE.name}."
        )
        print("Run `py tools/update_terms.py` from the mkdocs folder, then rerun this generator.")
        raise SystemExit(1)

    search_forms[canonical_term].update(parts[1:])

# Map every form back to its canonical term.
form_to_term = {}

for term, forms in search_forms.items():
    for form in forms:
        form_key = form.casefold()

        if form_key in form_to_term and form_to_term[form_key] != term:
            print(
                f"HEY! Search form `{form}` belongs to both "
                f"`{form_to_term[form_key]}` and `{term}`."
            )
            raise SystemExit(1)

        form_to_term[form_key] = term

# Match longer terms before shorter overlapping terms.
ordered_forms = sorted(
    (form for forms in search_forms.values() for form in forms),
    key=len,
    reverse=True,
)

term_pattern = re.compile(
    r"(?<!\w)("
    + "|".join(re.escape(form) for form in ordered_forms)
    + r")(?!\w)",
    re.IGNORECASE,
)


# DETECT LIFECYCLE STAGES

stage_id_lookup = {name: stage_id for stage_id, name, _ in LIFECYCLE_STAGES}

# Reuse the Markdown exclusions from variant_scanner.py.
heading_pattern = re.compile(r"^\s{0,3}#{1,6}\s+.*$", re.MULTILINE)

table_separator_pattern = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)

markdown_link_pattern = re.compile(
    r"!?\[[^\]]*\]\([^)]*\)", re.DOTALL
)

term_stages = {entry["term"]: [] for entry in glossary_entries}
stage_counts = {}

for _, stage_name, chapter_path in LIFECYCLE_STAGES:
    markdown = chapter_path.read_text(encoding="utf-8")

    # Remove headings.
    markdown = heading_pattern.sub(" ", markdown)

    # Remove table headers and separators.
    page_lines = markdown.splitlines()

    for index, line in enumerate(page_lines):
        if table_separator_pattern.match(line):
            if index > 0:
                page_lines[index - 1] = ""
            page_lines[index] = ""

    markdown = "\n".join(page_lines)

    # Remove existing Markdown links and images.
    markdown = markdown_link_pattern.sub(" ", markdown)

    # Treat line wrapping as spaces.
    markdown = re.sub(r"\s+", " ", markdown)

    # Record each canonical term only once per chapter.
    found_terms = set()

    for match in term_pattern.finditer(markdown):
        found_form = match.group(1)
        canonical_term = form_to_term[found_form.casefold()]
        found_terms.add(canonical_term)

    for term in found_terms:
        term_stages[term].append(stage_name)

    stage_counts[stage_name] = len(found_terms)


# READ MANUAL STAGE ASSIGNMENTS

valid_stages = set(stage_id_lookup)
manual_stages = {}

for line_number, line in enumerate(MANUAL_STAGES_SOURCE.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip() or line.lstrip().startswith("#"):
        continue

    parts = [part.strip() for part in line.split("|")]

    # Each line gives one canonical term followed by one or more lifecycle stages.
    # Example: Data visualization | Data Preparation | Results & Reporting
    if len(parts) < 2 or not all(parts):
        print(f"HEY! Invalid manual assignment on line {line_number}: {line}")
        raise SystemExit(1)

    term, *stages = parts

    if term not in term_stages:
        print(f"HEY! Unknown glossary term in {MANUAL_STAGES_SOURCE.name}: {term}")
        raise SystemExit(1)

    for stage in stages:
        if stage not in valid_stages:
            print(f"HEY! Unknown lifecycle stage for `{term}`: {stage}")
            raise SystemExit(1)

    if len(stages) != len(set(stages)):
        print(f"HEY! Repeated lifecycle stage for `{term}` on line {line_number}.")
        raise SystemExit(1)

    if term in manual_stages:
        print(f"HEY! Duplicate manual assignment for `{term}`.")
        raise SystemExit(1)

    manual_stages[term] = stages


# ADD LIFECYCLE INFORMATION

for entry in glossary_entries:
    term = entry["term"]
    stages = term_stages[term]

    if stages:
        entry["stages"] = stages
        entry["first_stage"] = stages[0]
        entry["stage_source"] = "automatic"
    elif term in manual_stages:
        entry["stages"] = manual_stages[term]
        entry["first_stage"] = manual_stages[term][0]
        entry["stage_source"] = "manual"
    else:
        entry["stages"] = []
        entry["first_stage"] = None
        entry["stage_source"] = "none"

    # Keep filter IDs separate from the full lifecycle labels displayed on cards.
    entry["stage_ids"] = [stage_id_lookup[stage] for stage in entry["stages"]]


# READ AND VALIDATE RELATIONSHIPS

# The spreadsheet supplies both labels for parent–child relationships.
# Peer relationships use the same spreadsheet label in both directions.
# Keep slash-separated singular/plural forms intact for the card renderer.

relationships_by_term = {entry["term"]: [] for entry in glossary_entries}
seen_pairs = {}
relationship_counts = {}
parent_child_count = 0
peer_count = 0

workbook = load_workbook(RELATIONSHIPS_SOURCE, read_only=True, data_only=True)

# Read the sorting priorities from the Labels worksheet.
# Each row gives one display label and its priority, regardless of direction.

if LABELS_SHEET not in workbook.sheetnames:
    print(f"HEY! Missing worksheet `{LABELS_SHEET}` in {RELATIONSHIPS_SOURCE.name}.")
    raise SystemExit(1)

labels_sheet = workbook[LABELS_SHEET]
label_headers = [
    str(value).strip() if value is not None else ""
    for value in next(labels_sheet.iter_rows(max_row=1, values_only=True))
]
label_columns = ("Sort_Order", "Display_Label")
missing_columns = [column for column in label_columns if label_headers.count(column) != 1]

if missing_columns:
    print(f"HEY! Missing or repeated columns in `{LABELS_SHEET}`: {', '.join(missing_columns)}.")
    raise SystemExit(1)

label_positions = {column: label_headers.index(column) for column in label_columns}
sort_order_by_label = {}

for row_number, row in enumerate(labels_sheet.iter_rows(min_row=2, values_only=True), 2):
    label = (
        str(row[label_positions["Display_Label"]]).strip()
        if label_positions["Display_Label"] < len(row) and row[label_positions["Display_Label"]] is not None
        else ""
    )

    if not label:
        continue

    order = row[label_positions["Sort_Order"]] if label_positions["Sort_Order"] < len(row) else None
    if (isinstance(order, bool) or not isinstance(order, (int, float))
            or not float(order).is_integer() or order < 1):
        print(f"HEY! Invalid Sort_Order in `{LABELS_SHEET}` row {row_number}.")
        raise SystemExit(1)

    if label in sort_order_by_label:
        print(f"HEY! Repeated Display_Label `{label}` in `{LABELS_SHEET}` row {row_number}.")
        raise SystemExit(1)

    sort_order_by_label[label] = int(order)

# Read relationship assignments from the other worksheet.

if RELATIONSHIPS_SHEET not in workbook.sheetnames:
    print(f"HEY! Missing worksheet `{RELATIONSHIPS_SHEET}` in {RELATIONSHIPS_SOURCE.name}.")
    raise SystemExit(1)

sheet = workbook[RELATIONSHIPS_SHEET]
headers = [str(value).strip() if value is not None else "" for value in next(sheet.iter_rows(max_row=1, values_only=True))]
required_columns = (
    "Parent", "Child", "P_C_Label", "C_P_Label",
    "Peer_1", "Peer_2", "Peer_Label",
)

missing_columns = [column for column in required_columns if headers.count(column) != 1]
if missing_columns:
    print(f"HEY! Missing or repeated spreadsheet columns: {', '.join(missing_columns)}.")
    raise SystemExit(1)

column_positions = {column: headers.index(column) for column in required_columns}

# Each spreadsheet row may contain a parent–child pair, a peer pair, or both.
# Blank values on either side are allowed, but partially filled relationships are not.

for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
    values = {
        column: str(row[position]).strip() if position < len(row) and row[position] is not None else ""
        for column, position in column_positions.items()
    }

    pairs = (
        ("parent–child", values["Parent"], values["Child"],
         values["P_C_Label"], values["C_P_Label"]),
        ("peer", values["Peer_1"], values["Peer_2"],
         values["Peer_Label"], values["Peer_Label"]),
    )

    for relationship_type, term1, term2, label1, label2 in pairs:
        if not any((term1, term2, label1, label2)):
            continue

        if not all((term1, term2, label1, label2)):
            print(f"HEY! Incomplete {relationship_type} relationship on spreadsheet row {row_number}.")
            raise SystemExit(1)

        for term in (term1, term2):
            if term not in relationships_by_term:
                print(f"HEY! Unknown canonical glossary term on spreadsheet row {row_number}: {term}")
                raise SystemExit(1)

        if term1 == term2:
            print(f"HEY! Self-link on spreadsheet row {row_number}: {term1}")
            raise SystemExit(1)

        # A pair can appear only once, regardless of direction or relationship type.
        pair_key = frozenset((term1, term2))
        if pair_key in seen_pairs:
            print(
                f"HEY! Duplicate relationship pair on spreadsheet rows "
                f"{seen_pairs[pair_key]} and {row_number}: {term1} | {term2}"
            )
            raise SystemExit(1)
        seen_pairs[pair_key] = row_number

        # Look up every display label in the Labels worksheet.
        # A combined peer label uses both singular and plural forms, which must
        # have the same priority. Keep its original text for the Ionic cards.
        for label in (label1, label2):
            label_parts = [part.strip() for part in label.split(" / ")]

            if any(part not in sort_order_by_label for part in label_parts):
                print(f"HEY! Missing Sort_Order for `{label}` on spreadsheet row {row_number}.")
                raise SystemExit(1)

            priorities = {sort_order_by_label[part] for part in label_parts}
            if len(priorities) != 1:
                print(f"HEY! Conflicting Sort_Order values for `{label}` on spreadsheet row {row_number}.")
                raise SystemExit(1)

            sort_order_by_label[label] = priorities.pop()

        # Keep the exact spreadsheet labels and attach their display priorities.
        relationships_by_term[term1].append({
            "label": label1, "term": term2, "sort_order": sort_order_by_label[label1],
        })
        relationships_by_term[term2].append({
            "label": label2, "term": term1, "sort_order": sort_order_by_label[label2],
        })
        relationship_counts[label1] = relationship_counts.get(label1, 0) + 1

        if relationship_type == "parent–child":
            parent_child_count += 1
        else:
            peer_count += 1

workbook.close()

for entry in glossary_entries:
    entry["relationships"] = sorted(
        relationships_by_term[entry["term"]],
        key=lambda link: (link["sort_order"], link["label"].casefold(), link["term"].casefold()),
    )


# LINK TERMS WITHIN GLOSSARY DEFINITIONS

# The relationship pairs have already been validated against canonical terms.
# A curated relationship takes precedence regardless of direction.
# Protect inline Markdown links/images, single-backtick code, HTML tags, and http(s) URLs.
# Reference-style links and multi-backtick code are not protected by this pattern.
protected_markdown = re.compile(
    r"(!?\[[^\]]*\]\([^)]*\)|`[^`]*`|<[^>]*>|https?://[^\s)]+)",
    re.DOTALL,
)

# Use the same ASCII slug rules as the Ionic card renderer.
# For example, AI/ML workflow becomes #aiml-workflow.
definition_link_count = 0
curated_pairs_skipped = set()
linked_definition_count = 0

for entry in glossary_entries:
    current_term = entry["term"]
    marked = {}
    linked_parts = []
    links_before = definition_link_count

    for part in protected_markdown.split(entry["definition"]):
        if protected_markdown.fullmatch(part):
            linked_parts.append(part)
            continue

        # Longest term forms match first. All variants resolve to canonical terms.
        output = []
        previous_end = 0

        for match in term_pattern.finditer(part):
            output.append(part[previous_end:match.start()])
            found = match.group(1)
            target_term = form_to_term[found.casefold()]
            previous_end = match.end()

            # Never link a glossary term to itself.
            if target_term == current_term:
                output.append(found)
                continue

            # The relationship spreadsheet is authoritative in both directions.
            pair = frozenset((current_term, target_term))
            if pair in seen_pairs:
                curated_pairs_skipped.add(pair)
                output.append(found)
                continue

            # Each definition has its own first-occurrence counter.
            marked[target_term] = marked.get(target_term, 0) + 1
            if MARKS_PER_DEFINITION and marked[target_term] > MARKS_PER_DEFINITION:
                output.append(found)
                continue

            anchor = unicodedata.normalize("NFKD", target_term)
            anchor = anchor.encode("ascii", "ignore").decode("ascii")
            anchor = re.sub(r"[^\w\s-]", "", anchor).strip().lower()
            anchor = re.sub(r"[-\s]+", "-", anchor)
            output.append(f"[{found}](#{anchor})")
            definition_link_count += 1

        output.append(part[previous_end:])
        linked_parts.append("".join(output))

    if definition_link_count > links_before:
        linked_definition_count += 1

    # Replace the existing JSON definition; the Markdown source stays untouched.
    entry["definition"] = "".join(linked_parts)


# WRITE THE JSON FILE

# Add the generation date above the glossary entries.
# This uses the date of the computer running the script.
glossary_data = {
    "generated_on": date.today().isoformat(),
    "terms": glossary_entries,
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE.write_text(
    json.dumps(glossary_data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)


# REPORT THE RESULTS

# Keep the terminal short. Full statistics are saved with the generated JSON.
automatic_count = sum(entry["stage_source"] == "automatic" for entry in glossary_entries)
manual_count = sum(entry["stage_source"] == "manual" for entry in glossary_entries)
unassigned_count = sum(entry["stage_source"] == "none" for entry in glossary_entries)
terms_with_relationships = sum(bool(entry["relationships"]) for entry in glossary_entries)
ignored_manual = [term for term in manual_stages if term_stages[term]]

report_lines = [
    f"Glossary generation report — {glossary_data['generated_on']}",
    "",
    f"Glossary terms exported: {len(glossary_entries)}",
    f"Terms found in lifecycle chapters: {automatic_count}",
    f"Terms assigned manually: {manual_count}",
    f"Terms without any stage: {unassigned_count}",
    f"JSON output: {OUTPUT_FILE.name}",
    f"First term: {glossary_entries[0]['term']}",
    f"Last term: {glossary_entries[-1]['term']}",
    "",
    "LIFECYCLE STAGE COUNTS",
]

for _, stage_name, _ in LIFECYCLE_STAGES:
    report_lines.append(f"  {stage_name}: {stage_counts[stage_name]} glossary terms")

report_lines.extend([
    "",
    "CURATED RELATIONSHIPS",
    f"Parent–child relationships imported: {parent_child_count}",
    f"Peer relationships imported: {peer_count}",
    f"Glossary terms with relationships: {terms_with_relationships}",
])

for label, count in sorted(relationship_counts.items()):
    report_lines.append(f"  {label}: {count}")

report_lines.extend([
    "",
    "DEFINITION CROSS-LINKS",
    f"Automatic cross-links added: {definition_link_count}",
    f"Definitions containing eligible cross-links: {linked_definition_count}",
    f"Curated relationship pairs found in definitions (excluded): {len(curated_pairs_skipped)}",
    f"First-occurrence limit per definition: {MARKS_PER_DEFINITION} (0 means unlimited)",
    "",
    "MANUAL STAGE ASSIGNMENTS",
])

if manual_count:
    for entry in glossary_entries:
        if entry["stage_source"] == "manual":
            report_lines.append(f"  {entry['term']} | {' | '.join(entry['stages'])}")
else:
    report_lines.append("  None")

report_lines.extend(["", "UNASSIGNED TERMS"])
if unassigned_count:
    for entry in glossary_entries:
        if entry["stage_source"] == "none":
            report_lines.append(f"  {entry['term']}")
else:
    report_lines.append("  None")

report_lines.extend(["", "MANUAL ASSIGNMENTS IGNORED (AUTOMATIC MATCHES EXIST)"])
if ignored_manual:
    for term in ignored_manual:
        report_lines.append(f"  {term}")
else:
    report_lines.append("  None")

REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

print(f"HEY! Glossary JSON generated: {len(glossary_entries)} terms, "
      f"{unassigned_count} unassigned, {definition_link_count} definition links.")
print(f"Curated relationships: {parent_child_count} parent–child, {peer_count} peer.")
print(f"Output: {OUTPUT_FILE.name} | Report: {REPORT_FILE.name}")

if unassigned_count:
    print("HEY! Glossary terms without a lifecycle stage:")
    for entry in glossary_entries:
        if entry["stage_source"] == "none":
            print(f"  {entry['term']}")
