from abc import ABC, abstractmethod
from extraction_utils import clean_html_text, parse_html_tables


class BaseSectionPlugin(ABC):
    def __init__(self, rules):
        self.rules = rules

    @property
    @abstractmethod
    def section_name(self):
        """The name of the section this plugin handles (must match rule.json)."""
        pass

    @abstractmethod
    def identify(self, text):
        """
        Determine if this section exists in the text.
        Returns True/False.
        """
        pass

    @abstractmethod
    def extract(self, text):
        """
        Extract data from the text.
        Returns a dictionary of extracted data.
        """
        pass

    def check_conditions(self, text, condition):
        """Helper to check rule conditions."""
        if isinstance(condition, str):
            return condition in text

        if isinstance(condition, list):
            return all(self.check_conditions(text, item) for item in condition)

        if isinstance(condition, dict):
            if "all_of" in condition:
                return all(
                    self.check_conditions(text, item) for item in condition["all_of"]
                )
            if "any_of" in condition:
                return any(
                    self.check_conditions(text, item) for item in condition["any_of"]
                )
            if "none_of" in condition:
                return not any(
                    self.check_conditions(text, item) for item in condition["none_of"]
                )
            if "contains" in condition:
                return condition["contains"] in text
        return False

    def clean_html(self, text):
        """Remove HTML tags and entities."""
        return clean_html_text(text)

    def parse_html_tables(self, text):
        """
        Parse ALL HTML tables in text.
        Returns list of (rows, headers) tuples.
        """
        return parse_html_tables(text)
