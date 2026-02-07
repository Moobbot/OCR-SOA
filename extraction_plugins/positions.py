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
                page_id = section.get("page_identification", {})

                # Logic copied from original script, using helper
                match = False
                if "primary_check" in page_id:
                    match = self.check_conditions(text, page_id["primary_check"])
                elif "any_of" in page_id:
                    match = self.check_conditions(text, {"any_of": page_id["any_of"]})
                elif "all_of" in page_id:
                    match = self.check_conditions(text, {"all_of": page_id["all_of"]})

                return match
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

        # Portfolio No.
        if "Portfolio No." in extraction_rules:
            rule = extraction_rules["Portfolio No."]
            if "regex" in rule:
                match = re.search(rule["regex"], text)
                if match:
                    data["Portfolio No."] = match.group(0)

        # Others can be added here

        return data
