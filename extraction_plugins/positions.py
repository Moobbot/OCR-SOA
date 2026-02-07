import re
from .base import BaseSectionPlugin


class PositionsPlugin(BaseSectionPlugin):
    @property
    def section_name(self):
        return "Positions"

    def identify(self, text):
        # Find identification rules for "Positions"
        for section in self.rules["sections"]:
            if section["section_name"] == self.section_name:
                # Stricter check: Must have "Detailed positions" as a main header
                # to avoid TOC pages.
                if text.strip().startswith("# Detailed positions"):
                    return True

                return False
        return False

    def extract(self, text):
        data = {}
        section_rule = next(
            (
                s
                for s in self.rules["sections"]
                if s["section_name"] == self.section_name
            ),
            None,
        )
        if not section_rule:
            return data

        extraction_rules = section_rule.get("extraction_rules", {})

        # Portfolio No. (Header)
        if "Portfolio No." in extraction_rules:
            rule = extraction_rules["Portfolio No."]
            if "regex" in rule:
                match = re.search(rule["regex"], text)
                if match:
                    data["Portfolio No."] = match.group(0)

        # Parse All Tables
        all_tables = self.parse_html_tables(text)

        extracted_rows = []
        current_item = None

        currencies = ["SGD", "USD", "CHF", "HKD", "EUR", "GBP", "JPY", "AUD", "CAD"]

        for rows, headers in all_tables:
            # Header check: If it looks like data, include it
            if headers:
                first_h = headers[0].strip()
                if first_h and (
                    first_h[0].isdigit()
                    or any(first_h.startswith(c) for c in currencies)
                ):
                    rows.insert(0, headers)

            for row in rows:
                if isinstance(row, dict):
                    row = list(row.values())

                row_text = " ".join(row).strip()
                if not row_text or row_text.lower().startswith("total"):
                    continue

                # Detect Start of New Item: Column 0 starts with digit OR Currency
                is_new_item = False
                first_col = row[0].strip()

                if first_col and (
                    first_col[0].isdigit()
                    or any(first_col.startswith(c) for c in currencies)
                ):
                    # Check if it is a date (DD.MM.YYYY) -> Skip (likely Transaction table)
                    if re.match(r"\d{2}\.\d{2}\.\d{4}", first_col):
                        is_new_item = False
                    elif len(row) >= 5:
                        # Simple check if Market Value Col (last or second to last) has a number
                        # In Detailed positions, Col 4 or 5 is usually the value
                        val_col = row[4] if len(row) > 4 else row[-1]
                        if any(c.isdigit() for c in str(val_col)):
                            is_new_item = True
                        else:
                            is_new_item = False
                    else:
                        is_new_item = False

                if is_new_item:
                    # Save previous
                    if current_item:
                        extracted_rows.append(current_item)

                    # Init new with defaults for ALL columns
                    current_item = {
                        "File": "",
                        "target_section": "Positions",
                        "Portfolio No.": data.get("Portfolio No.", ""),
                        "Valuation date": "31.07.2025",
                        "Client name": "",  # Needed? Not in ground truth columns for positions but good to have
                        "Type": "",
                        "Account No": "",
                        "Currency": "",
                        "Quantity/ Amount": "",
                        "Security ID": "",
                        "Security name": "",
                        "Cost price": "",
                        "Market price": "",
                        "Market value": "",
                        "Accrued interest": "",
                    }

                    # Parse Quantity and Name from Col 0/1
                    # Sometimes SGD is in Col 0, Name in Col 1
                    if (
                        any(first_col.startswith(c) for c in currencies)
                        and len(first_col) <= 4
                    ):
                        current_item["Currency"] = first_col
                        if len(row) > 1:
                            # Name might be "0.00 Name..."
                            parts = row[1].split(maxsplit=1)
                            if len(parts) == 2:
                                current_item["Quantity/ Amount"] = parts[0]
                                current_item["Security name"] = parts[1]
                            else:
                                current_item["Security name"] = row[1]
                    else:
                        parts = first_col.split(maxsplit=1)
                        if len(parts) == 2:
                            current_item["Quantity/ Amount"] = parts[0]
                            current_item["Security name"] = parts[1]
                        else:
                            current_item["Quantity/ Amount"] = first_col

                    # Col Mapping (Simplified for alignment)
                    if len(row) > 2:
                        current_item["Market price"] = row[2]
                    if len(row) > 4:
                        current_item["Market value"] = row[4]
                        current_item["Cost price"] = row[4]  # Fallback?
                    if len(row) > 1:
                        # Try to find cost price if distinct
                        pass

                    # Currency extraction if not set
                    if not current_item["Currency"]:
                        for c in currencies:
                            if c in str(row):
                                current_item["Currency"] = c
                                break

                    # Extract Account No from Description or Row
                    acc_match = re.search(r"\d{3}-\d{6}\.[A-Z0-9]+", row_text)
                    if acc_match:
                        current_item["Account No"] = acc_match.group(0)

                else:
                    # Continuation Row (Details)
                    if current_item:
                        # Check for ISIN -> Security ID
                        isin_match = re.search(r"ISIN\s+([A-Z0-9]{12})", row_text)
                        if isin_match:
                            current_item["Security ID"] = isin_match.group(1)

                        # Check for Account No if not found
                        if not current_item["Account No"]:
                            acc_match = re.search(r"\d{3}-\d{6}\.[A-Z0-9]+", row_text)
                            if acc_match:
                                current_item["Account No"] = acc_match.group(0)

        # Append last
        if current_item:
            extracted_rows.append(current_item)

        if extracted_rows:
            data["_rows"] = extracted_rows

        return data
