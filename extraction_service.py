import json
import os
import pandas as pd
from extraction_plugins import get_all_plugins


def load_rules(rule_path):
    if not os.path.exists(rule_path):
        print(f"Error: {rule_path} not found.")
        return {}
    with open(rule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def initialize_system(rule_path="rule.json"):
    """
    Load rules and initialize plugins.
    Returns: plugins list
    """
    rules = load_rules(rule_path)
    if not rules:
        return []

    plugins = get_all_plugins(rules)
    print(f"Initialized {len(plugins)} plugins: {[p.section_name for p in plugins]}")
    return plugins


def normalize_text(text):
    """Step 1: Normalize text (case-insensitive, collapse spaces)."""
    if not text:
        return ""
    # Collapse multiple spaces
    text = " ".join(text.split())
    # Note: We keep the original text for extraction values, but use normalized for classification?
    # The user said "case-insensitive; collapse spaces; remove OCR garbage".
    # We will simply return the cleaned text. Case-insensitivity will be handled during matching.
    return text


def classify_page(text, rules):
    """Step 2: Classify Page-level."""
    # Default to Ignore
    page_type = "Ignore"

    if not rules or "page_classification" not in rules:
        return "Ignore"

    page_rules = rules["page_classification"].get("rules", [])

    # Sort rules by priority (descending)
    sorted_rules = sorted(page_rules, key=lambda x: x.get("priority", 0), reverse=True)

    # We need to check headers basically.
    # Simple heuristic: Look at the first few lines or # headers.
    lines = text.split("\n")
    headers = [line for line in lines if line.strip().startswith("#")]
    # If no markdown headers, maybe take first 5 lines?
    header_text = "\n".join(headers) if headers else "\n".join(lines[:10])

    normalized_header = header_text.lower()

    for rule in sorted_rules:
        if rule.get("fallback"):
            # If we reach fallback, set it (usually Ignore)
            page_type = rule.get("type", "Ignore")
            continue

        match_in = rule.get("match_in", "header")
        contains_any = rule.get("contains_any", [])

        # Check conditions
        matched = False
        if match_in == "header":
            # Check against header text
            for keyword in contains_any:
                if keyword.lower() in normalized_header:
                    matched = True
                    break

        if matched:
            return rule.get("type")

    return page_type


def classify_record(row_text, rules):
    """Step 4: Classify Record (only for Transaction pages)."""
    # Default
    txn_group = "Trade"
    txn_type = "Trade"

    if not rules or "record_classification" not in rules:
        return txn_group, txn_type

    rec_rules = rules["record_classification"].get("rules", [])
    # Sort
    sorted_rules = sorted(rec_rules, key=lambda x: x.get("priority", 0), reverse=True)

    row_lower = row_text.lower()

    for rule in sorted_rules:
        if rule.get("fallback"):
            txn_group = rule.get("output_group", "Trade")
            txn_type = rule.get("output", "Trade")
            continue

        match_any = rule.get("match_any", [])
        matched = False
        for keyword in match_any:
            if keyword.lower() in row_lower:
                matched = True
                break

        if matched:
            return rule.get("output_group"), rule.get("output")

    return txn_group, txn_type


def extract_from_text(text, filename, plugins, rules):
    """
    Process a single text block (page) using the 4-step flow.
    """
    extracted_results = {}

    # Step 1: Normalize (Conceptually - we use raw text for extraction but normalized for checks)
    # text = normalize_text(text) # In practice, plugins need original structure. Matches are case-insensitive.

    # Step 2: Classify Page
    page_type = classify_page(text, rules)
    print(f"Page {filename} classified as: {page_type}")

    if page_type == "Ignore" or page_type == "Unknown":
        return {}

    # Step 3: Process by Page Type
    if page_type == "Positions":
        # 3.1 Run positions extractor
        # Find PositionsPlugin
        pos_plugin = next((p for p in plugins if p.section_name == "Positions"), None)
        if pos_plugin:
            data = pos_plugin.extract(text)
            if data:
                extracted_results["Positions"] = []
                if "_rows" in data:
                    for row in data["_rows"]:
                        # Ensure row has basic fields
                        row["File"] = filename
                        if "row_text" in row:
                            # row["Row Text"] = row["row_text"] # User requested removal
                            row.pop("row_text")
                        extracted_results["Positions"].append(row)

    elif page_type == "Transaction":
        # 3.2 Extract list of transactions
        # Find TradeInformationPlugin
        trade_plugin = next(
            (p for p in plugins if p.section_name == "Trade information"), None
        )
        if trade_plugin:
            data = trade_plugin.extract(text)
            # Expecting data["_rows"] with raw rows
            raw_rows = data.get("_rows", [])

            # Step 4: Classify individual transactions
            # 4.1, 4.2, 4.3 priorities handled by classify_record
            for row in raw_rows:
                row_text = row.get("row_text", "")
                if not row_text and isinstance(row, dict):
                    # Construct row text if missing
                    vals = [
                        str(v)
                        for k, v in row.items()
                        if k not in ["File", "target_section"]
                    ]
                    row_text = " ".join(vals)

                txn_group, txn_type = classify_record(row_text, rules)

                # Standardize row keys
                row["File"] = filename
                # row["Row Text"] = row_text # User requested removal
                if "row_text" in row:
                    row.pop("row_text")

                # Ensure all rule columns are present? No, let pandas handle NaN
                row["Type"] = txn_type
                row["target_section"] = txn_group  # This will be FXFT, Others, or Trade

                # Add to results
                if txn_group not in extracted_results:
                    extracted_results[txn_group] = []
                extracted_results[txn_group].append(row)

    return extracted_results


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
        "Trade": "trade",
        "trade": "trade",
        "FXFT": "FXFT",
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
