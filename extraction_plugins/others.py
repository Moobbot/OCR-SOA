from .base import BaseSectionPlugin


class OthersPlugin(BaseSectionPlugin):
    @property
    def section_name(self):
        return "Others"

    def identify(self, text):
        for section in self.rules["sections"]:
            if section["section_name"] == self.section_name:
                page_id = section.get("page_identification", {})
                if "fallback" in page_id and page_id["fallback"]:
                    return True
        return False

    def extract(self, text):
        return {}
