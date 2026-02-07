from abc import ABC, abstractmethod


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
        import re

        # Remove tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Simple entity decoding (expand as needed)
        clean = (
            clean.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        return clean.strip()

    def parse_html_tables(self, text):
        """
        Parse ALL HTML tables in text.
        Returns list of (rows, headers) tuples.
        """
        import re

        tables = []
        table_matches = re.finditer(r"<table>(.*?)</table>", text, re.DOTALL)

        for match in table_matches:
            table_content = match.group(1)

            # Parse headers
            headers = []
            thead_match = re.search(r"<thead>(.*?)</thead>", table_content, re.DOTALL)
            if thead_match:
                header_row = re.findall(
                    r"<th>(.*?)</th>", thead_match.group(1), re.DOTALL
                )
                headers = [self.clean_html(h) for h in header_row]

            # Parse rows
            rows = []
            tbody_match = re.search(r"<tbody>(.*?)</tbody>", table_content, re.DOTALL)
            if tbody_match:
                tr_matches = re.findall(
                    r"<tr>(.*?)</tr>", tbody_match.group(1), re.DOTALL
                )
                for tr in tr_matches:
                    # Capture cell content, handle empty cells
                    td_matches = re.findall(r"<td>(.*?)</td>", tr, re.DOTALL)
                    row_values = [self.clean_html(td) for td in td_matches]

                    # If we have headers and lengths match, create a dict
                    if headers and len(headers) == len(row_values):
                        rows.append(dict(zip(headers, row_values)))
                    elif headers:
                        # Attempt strict alignment or just return list?
                        # Return dict with best effort or just list?
                        # List is safer if mismatch.
                        rows.append(row_values)
                    else:
                        rows.append(row_values)

            tables.append((rows, headers))

        return tables
