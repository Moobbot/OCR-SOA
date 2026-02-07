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
            # Simple mock logic from previous script
            if "Portfolio number" in text and "Statement of assets" in text:
                pattern = r"Portfolio number.*?\n(.*?)\n.*?Statement of assets"
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    data["Client name"] = match.group(1).strip()

        # Simulate Row Classification (Mock)
        if "transaction_type_rules" in self.rules:
            data["_rows"] = []
            lines = text.split("\n")
            classifiers = self.rules.get("transaction_type_rules", [])

            # Helper: Instantiate FX plugin to check its conditions
            from .fx_tf import FXTFPlugin

            fx_plugin = FXTFPlugin(self.rules)

            for row in lines:
                row = row.strip()
                if not row or "---" in row:
                    continue

                # Mock: Try to clean HTML tags for cleaner classification
                clean_row = re.sub(r"<[^>]+>", " ", row).strip()
                # Remove extra spaces
                clean_row = re.sub(r"\s+", " ", clean_row)

                if len(clean_row) < 5:
                    continue

                # 1. Check strict FX condition from FXTFPlugin
                is_fx, fx_type = fx_plugin.is_fx_transaction(clean_row)
                if is_fx:
                    item = {
                        "row_text": clean_row,
                        "type": fx_type,
                        "target_section": "FX & TF",
                    }
                    data["_rows"].append(item)
                    continue

                # 2. Generic Trade Information Classification
                trans_type = "Other"
                sorted_classifiers = sorted(
                    classifiers, key=lambda x: x.get("priority", 0), reverse=True
                )

                matched_rule = None
                for rule in sorted_classifiers:
                    is_match = False
                    if "match_any" in rule:
                        is_match = any(
                            k.lower() in clean_row.lower() for k in rule["match_any"]
                        )

                    if is_match:
                        if "exclude_if_contains" in rule:
                            if any(
                                e.lower() in clean_row.lower()
                                for e in rule["exclude_if_contains"]
                            ):
                                is_match = False

                    if is_match:
                        matched_rule = rule
                        trans_type = rule["output"]
                        break

                # Only add if it's a classified transaction OR looks like a table row of interest
                if trans_type != "Other" or (
                    "SGD" in clean_row and any(c.isdigit() for c in clean_row)
                ):
                    item = {
                        "row_text": clean_row,
                        "type": trans_type,
                        "target_section": "Trade information",
                    }
                    data["_rows"].append(item)

        return data
