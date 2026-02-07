from .base import BaseSectionPlugin


class FXTFPlugin(BaseSectionPlugin):
    @property
    def section_name(self):
        return "FX & TF"

    def identify(self, text):
        for section in self.rules["sections"]:
            if section["section_name"] == self.section_name:
                page_id = section.get("page_identification", {})

                match = False
                if "primary_check" in page_id:
                    match = self.check_conditions(text, page_id["primary_check"])

                if match:
                    if "subtype_check" in page_id:
                        sub = page_id["subtype_check"]
                        if "any_of" in sub:
                            match = self.check_conditions(
                                text, {"any_of": sub["any_of"]}
                            )

                return match
        return False

    def extract(self, text):
        return {}

    def is_fx_transaction(self, row_text):
        """
        Check if a row string matches FX criteria based on 'transaction_type_rules'.
        """
        classifiers = self.rules.get("transaction_type_rules", [])
        # Only check against classifiers that output FX types
        fx_types = ["FX Spot", "FX Forward"]

        for rule in classifiers:
            if rule.get("output") not in fx_types:
                continue

            is_match = False
            if "match_any" in rule:
                is_match = any(k.lower() in row_text.lower() for k in rule["match_any"])

            if is_match:
                if "exclude_if_contains" in rule:
                    if any(
                        e.lower() in row_text.lower()
                        for e in rule["exclude_if_contains"]
                    ):
                        is_match = False

            if is_match:
                return True, rule["output"]

        return False, None
