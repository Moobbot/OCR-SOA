import re
from .base import BaseSectionPlugin


class TradeInformationPlugin(BaseSectionPlugin):
    @property
    def section_name(self):
        return "Trade information"

    def identify(self, text):
        for section in self.rules["sections"]:
            if section["section_name"] == self.section_name:
                page_id = section.get("page_identification", {})

                # Check primary
                primary_match = False
                if "primary_check" in page_id:
                    primary_match = self.check_conditions(
                        text, page_id["primary_check"]
                    )

                # Check subtype (if exists)
                subtype_match = True
                if "subtype_check" in page_id:
                    sub = page_id["subtype_check"]
                    if "any_of" in sub:
                        subtype_match = self.check_conditions(
                            text, {"any_of": sub["any_of"]}
                        )
                    elif "all_of" in sub:
                        subtype_match = self.check_conditions(
                            text, {"all_of": sub["all_of"]}
                        )

                return primary_match and subtype_match
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

        # Client name (Logic based)
        if "Client name" in extraction_rules:
            if "Portfolio number" in text and "Statement of assets" in text:
                pattern = r"Portfolio number.*?\n(.*?)\n.*?Statement of assets"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    data["Client name"] = match.group(1).strip()

        # Parse All Tables
        all_tables = self.parse_html_tables(text)

        extracted_rows = []

        for rows, headers in all_tables:
            # Heuristic: Check if header is actually a data row (contains date)
            if headers:
                # Check for DD.MM.YYYY
                if re.search(r"\d{2}\.\d{2}\.\d{4}", headers[0]):
                    # If header is data, prepend it to rows
                    # Headers variable becomes list of values, convert to list if needed
                    rows.insert(0, headers)
                    headers = []

            for row in rows:
                # Expecting list of values
                if isinstance(row, dict):
                    row = list(row.values())

                # Stricter Row Filtering: Must have a date in Col 0 AND a non-empty Transaction Type in Col 1
                is_valid_date = re.match(r"\d{2}\.\d{2}\.\d{4}", row[0].strip())
                has_type = len(row) > 1 and row[1].strip() != ""

                if not is_valid_date or not has_type:
                    continue

                row_text = " ".join(row)

                # --- Row Classification ---
                # Helper: Instantiate FX plugin to check its conditions
                # Optimization: Load once class-level or outside loop if slow
                from .fx_tf import FXTFPlugin

                fx_plugin = FXTFPlugin(self.rules)

                is_fx, fx_type = fx_plugin.is_fx_transaction(row_text)
                if is_fx:
                    item = {
                        "File": "",  # Filled by service
                        "row_text": row_text,
                        "target_section": "FX & TF",
                        "Type": fx_type,
                    }
                    # Map specific FX fields if possible (future task)
                    extracted_rows.append(item)
                    continue

                # --- Simplified Extraction (Delegate classification to Service) ---
                # Init with all columns
                item = {
                    "row_text": row_text,
                    "target_section": "Trade information",  # Default
                    "Type": "Trade",  # Default,
                    # Columns
                    "Client name": data.get("Client name", ""),
                    "Name/ Security": "",
                    "Securities ID": "",
                    "Transaction type": "",  # Col 4
                    "Trade date": "",  # Col 5
                    "Settlement date": "",  # Col 6
                    "Currency": "",  # Col 7
                    "Quantity": "",  # Col 8
                    "Account no.": "",  # Col 9
                    "Foreign Unit Price": "",  # Col 10
                    "Foreign Gross consideration": "",  # Col 11
                    "Foreign Net consideration": "",  # Col 12
                    "Net consideration": "",  # Col 13
                    "Commission fee (Base)": "",  # Col 14
                    "Accrued interest": "",  # Col 15
                    "Foreign Transaction Fee": "",  # Col 16
                }

                # 1. Trade Date (Col 0)
                if re.match(r"\d{2}\.\d{2}\.\d{4}", row[0]):
                    item["Trade date"] = row[0]
                    # Attempt to find Settlement Date (2nd date in row?)
                    dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", row_text)
                    if len(dates) > 1:
                        item["Settlement date"] = dates[1]  # Simple heuristic
                    else:
                        item["Settlement date"] = row[0]  # Default same?

                # 2. Transaction Type (Col 1)
                item["Transaction type"] = row[1].strip()

                # 3. Amount/Currency (Col 2)
                if len(row) > 2:
                    parts = row[2].split()
                    if len(parts) > 0 and parts[0].isalpha():
                        item["Currency"] = parts[0]
                        item["Foreign Net consideration"] = " ".join(
                            parts[1:]
                        )  # Value usually here
                        item["Net consideration"] = " ".join(parts[1:])
                    else:
                        item["Foreign Net consideration"] = row[2]
                        item["Net consideration"] = row[2]

                # 4. Security Name / Description (Col 3)
                if len(row) > 3:
                    item["Name/ Security"] = row[3]

                # 5. Foreign Unit Price (Col 4)
                if len(row) > 4:
                    item["Foreign Unit Price"] = row[4]

                # 6. Foreign Gross consideration (Col 7 - usually "Transaction value")
                if len(row) > 7:
                    item["Foreign Gross consideration"] = row[7]

                # Extract ISIN / Account from Text
                isin_match = re.search(r"ISIN\s+([A-Z0-9]{12})", row_text)
                if isin_match:
                    item["Securities ID"] = isin_match.group(1)

                acc_match = re.search(r"\d{3}-\d{6}\.[A-Z0-9]+", row_text)
                if acc_match:
                    item["Account no."] = acc_match.group(0)

                # Filter: Must have Trade date to be a "main" row
                if item["Trade date"]:
                    extracted_rows.append(item)

        if extracted_rows:
            data["_rows"] = extracted_rows

        return data
