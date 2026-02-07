import json
import os
import sys
import pandas as pd
from extraction_plugins import get_all_plugins


def load_rules(rule_path):
    with open(rule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    rule_path = "rule.json"
    output_dir = "outputs"
    output_excel = "extracted_data.xlsx"

    if not os.path.exists(rule_path):
        print(f"Error: {rule_path} not found.")
        return

    rules = load_rules(rule_path)
    print("Loaded rules.")

    # Initialize Plugins
    plugins = get_all_plugins(rules)
    print(f"Initialized {len(plugins)} plugins: {[p.section_name for p in plugins]}")

    # Data Containers (Dictionary sets to collect rows per sheet)
    # Keys should match Section Names strictly or be mapped
    all_data = {"Positions": [], "Trade information": [], "FX & TF": [], "Others": []}

    files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    files.sort()

    print(f"\n--- Processing {len(files)} files ---")

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # Identify active plugins for this page
        active_plugins = []
        for plugin in plugins:
            if plugin.identify(text):
                active_plugins.append(plugin)

        # Run extraction
        for plugin in active_plugins:
            data = plugin.extract(text)
            if not data:
                continue

            section = plugin.section_name

            # Handle row-based data (Trade Info / FX)
            if "_rows" in data:
                for row in data["_rows"]:
                    # Create a flattened row object
                    row_data = {
                        "File": filename,
                        "Row Text": row.get("row_text", ""),
                        "Type": row.get("type", ""),
                        # Include other metadata if extracted later
                    }

                    # Merge any top-level data extracted (e.g. Client Name) into each row?
                    # Or keep separate? Ideally tables are tables.
                    # If Client Name is extracted, it applies to the page.
                    # For filtering simplicity, we can duplicate it or put it in a separate header sheet.
                    # For this request, let's keep it simple: Just the table data + Classification

                    # Routing based on target_section
                    target = row.get("target_section", section)
                    if target in all_data:
                        all_data[target].append(row_data)
            else:
                # Handle single-page/header data (Positions)
                # Currently Positions plugin extracts "Portfolio No."
                flat_data = {"File": filename}
                flat_data.update(data)

                if section in all_data:
                    all_data[section].append(flat_data)

    # Export to Excel
    print(f"\n--- Exporting to {output_excel} ---")

    # Create directory for report if needed? No, user current dir.

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        for section, rows in all_data.items():
            # Sanitize sheet name
            sheet_name = section.replace("&", "and").replace("/", "-")[:31]

            if rows:
                df = pd.DataFrame(rows)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  Sheet '{sheet_name}': {len(rows)} rows")
            else:
                # Create empty sheet with columns if possible? Or just skip.
                # Create empty df with a Note
                pd.DataFrame({"Note": ["No data found"]}).to_excel(
                    writer, sheet_name=sheet_name, index=False
                )
                print(f"  Sheet '{sheet_name}': No data found")

    print(f"Successfully saved to {os.path.abspath(output_excel)}")


if __name__ == "__main__":
    main()
