import json
import re
import os
import sys


def load_rules(rule_path):
    with open(rule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_conditions(text, condition):
    if isinstance(condition, str):
        return condition in text

    if isinstance(condition, list):
        return all(check_conditions(text, item) for item in condition)

    if isinstance(condition, dict):
        if "all_of" in condition:
            return all(check_conditions(text, item) for item in condition["all_of"])
        if "any_of" in condition:
            return any(check_conditions(text, item) for item in condition["any_of"])
        if "none_of" in condition:
            return not any(
                check_conditions(text, item) for item in condition["none_of"]
            )
        if "contains" in condition:
            return condition["contains"] in text
    return False


def identify_section(text, rules):
    matched_sections = []
    for section in rules["sections"]:
        section_name = section["section_name"]
        page_id = section.get("page_identification", {})

        # Primary Check
        primary_match = False
        if "primary_check" in page_id:
            primary_match = check_conditions(text, page_id["primary_check"])
        elif "any_of" in page_id:
            primary_match = check_conditions(text, {"any_of": page_id["any_of"]})
        elif "all_of" in page_id:
            primary_match = check_conditions(text, {"all_of": page_id["all_of"]})
        elif "fallback" in page_id and page_id["fallback"]:
            primary_match = True

        # Subtype Check
        subtype_match = True
        if "subtype_check" in page_id:
            sub = page_id["subtype_check"]
            if "any_of" in sub:
                subtype_match = check_conditions(text, {"any_of": sub["any_of"]})
            elif "all_of" in sub:
                subtype_match = check_conditions(text, {"all_of": sub["all_of"]})

        if primary_match and subtype_match:
            matched_sections.append(section_name)

    return matched_sections


def extract_field(text, rule):
    # Regex extraction
    if "regex" in rule:
        match = re.search(rule["regex"], text)
        if match:
            return match.group(0)

    # Logic extraction (Simple implementation for demo)
    if "logic" in rule and "Portfolio number" in text and "Statement of assets" in text:
        # Example logic: "Text between portfolio number and 'Statement of assets'"
        pattern = r"Portfolio number.*?\n(.*?)\n.*?Statement of assets"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    return None


def main():
    rule_path = "rule.json"
    output_dir = "outputs"

    if not os.path.exists(rule_path):
        print(f"Error: {rule_path} not found.")
        return

    rules = load_rules(rule_path)
    print("Loaded rules.")

    # Test distinct files mentioned
    test_files = ["0218_page_10.md", "0218_page_12.md", "0218_page_17.md"]
    print("\n--- Value Extraction Demo ---")

    for tf in test_files:
        path = os.path.join(output_dir, tf)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            print(f"\nFile: {tf}")
            sections = identify_section(text, rules)
            print(f"Identified Sections: {sections}")

            # Try to extract common fields if section matches
            extracted_data = {}

            if "Positions" in sections:
                # Find rules for Positions
                for sec in rules["sections"]:
                    if sec["section_name"] == "Positions":
                        # Try extracting Portfolio No
                        p_rule = sec["extraction_rules"].get("Portfolio No.", {})
                        val = extract_field(text, p_rule)
                        extracted_data["Positions - Portfolio No."] = val

            if "Trade information" in sections or "Positions" in sections:
                # Client Name (Common rule logic)
                # Find rule in Trade info (usually Section 1)
                for sec in rules["sections"]:
                    if sec["section_name"] == "Trade information":
                        c_rule = sec["extraction_rules"].get("Client name", {})
                        val = extract_field(text, c_rule)
                        extracted_data["Client Name"] = val
                        break

            for k, v in extracted_data.items():
                if v:
                    print(f"  [EXTRACTED] {k}: {v}")
                else:
                    print(f"  [FAILED] {k}: Not found")


if __name__ == "__main__":
    main()
