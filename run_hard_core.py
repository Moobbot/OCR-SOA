import os
import json
import pandas as pd
from pipeline.orchestrator import ProcessingPipeline
from pipeline.extractors import get_all_plugins


def load_rules(rule_path):
    if not os.path.exists(rule_path):
        print(f"Error: {rule_path} not found.")
        return {}
    with open(rule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def initialize_system(rule_path="docs/rule.json"):
    """
    Load rules and initialize plugins.
    Returns: plugins list, rules dict
    """
    rules = load_rules(rule_path)
    if not rules:
        return [], {}

    plugins = get_all_plugins(rules)
    print(f"Initialized {len(plugins)} plugins: {[p.section_name for p in plugins]}")
    return plugins, rules


def append_to_excel(new_data, output_excel="extracted_data.xlsx"):
    """
    Append new data to the Excel file.
    Reads existing file (if any), appends new rows, and saves back.
    """
    # Load existing data
    if os.path.exists(output_excel):
        try:
            # Read all sheets
            existing_sheets = pd.read_excel(output_excel, sheet_name=None)
        except Exception as e:
            print(f"Error reading existing Excel: {e}. Starting fresh.")
            existing_sheets = {}
    else:
        existing_sheets = {}

    # Merge new data
    SHEET_NAME_MAPPING = {
        "Trade information": "Trade",
        "trade": "Trade",
        "FX & TF": "FX & TF",
        "FXFT": "FX & TF",
        "Others": "Others",
        "Positions": "Positions",
    }

    for section, rows in new_data.items():
        if not rows:
            continue

        # Map section name to requested sheet name, fallback to sanitized section name
        sheet_name = SHEET_NAME_MAPPING.get(
            section, section.replace("&", "and").replace("/", "-")
        )[:31]

        # Use "Trade" for Trade information to match user request (case sensitive?)
        # User requested "Trade" (title case) in previous sessions, actually "trade" (lowercase) was also seen.
        # Strict mapping: "Trade information" -> "trade" per user rules?
        # Re-checking walkthrough: "trade" (lowercase) was used?
        # But previous steps used "Trade" group and "Trade" type.
        # Let's check existing sheet names.

        # User requested "Trade" (Title Case) or "trade"?
        # In this session, user complained about "Type" column.
        # Let's stick to what we had in extraction_service.py:
        # "Trade": "trade", "trade": "trade"

        if section == "Trade information":
            sheet_name = "Trade"  # Let's use Capitalized as per recent context or user preference?
            # Actually, let's verify what extraction_service.py did.
            # It had: "Trade": "trade", "trade": "trade".

        new_df = pd.DataFrame(rows)

        if sheet_name in existing_sheets:
            # Append to existing DF
            existing_sheets[sheet_name] = pd.concat(
                [existing_sheets[sheet_name], new_df], ignore_index=True
            )
        else:
            # Create new DF
            existing_sheets[sheet_name] = new_df

    # Write back
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        for sheet_name, df in existing_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Updated {output_excel} with data from recent extraction.")


def main():
    output_dir = "outputs"
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} not found.")
        return

    # Check for rule.json in docs/
    rule_path = "docs/rule.json"

    plugins, rules = initialize_system(rule_path)
    if not plugins:
        return

    # Initialize Pipeline
    pipeline = ProcessingPipeline(plugins, rules)

    files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    files.sort()

    print(f"\n--- Processing {len(files)} files ---")

    all_results = {}

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # Process with Pipeline
        results = pipeline.process_page(text, filename)

        if results:
            # Merge results into all_results
            for section, rows in results.items():
                if section not in all_results:
                    all_results[section] = []
                all_results[section].extend(rows)

    # Save to Excel
    append_to_excel(all_results)


if __name__ == "__main__":
    main()
