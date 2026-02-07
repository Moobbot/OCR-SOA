from .base import BaseSectionPlugin


class OthersPlugin(BaseSectionPlugin):
    @property
    def section_name(self):
        return "Others"

    def identify(self, text):
        # Avoid identifying Performance, TOC, Allocation, or dummy pages as "Others"
        # because they create too much noise in this specific dataset.
        t_stripped = text.strip()
        if (
            t_stripped.startswith("# Performance")
            or t_stripped.startswith("# Table of contents")
            or t_stripped.startswith("# Asset evaluations")
            or t_stripped.startswith("# Asset allocation")
            or t_stripped.startswith("# Document Title")
            or t_stripped.startswith("# Important information")
            or t_stripped.startswith("# Portfolio overview")
        ):
            return False

        for section in self.rules["sections"]:
            if section["section_name"] == self.section_name:
                page_id = section.get("page_identification", {})
                if "fallback" in page_id and page_id["fallback"]:
                    return True
        return False

    def extract(self, text):
        data = {"target_section": "Others"}

        # Parse All Tables as Others
        all_tables = self.parse_html_tables(text)
        extracted_rows = []

        for rows, headers in all_tables:
            for row in rows:
                # Stricter Filtering for Others: Avoid empty/dummy rows
                # Must have at least two non-empty columns with some alphanumeric content
                cols_with_content = [
                    c
                    for c in row
                    if str(c).strip() and any(ch.isalnum() for ch in str(c))
                ]
                if len(cols_with_content) < 2:
                    continue

                if isinstance(row, dict):
                    row_data = row
                else:
                    # Generic list of values
                    row_data = {f"Col_{i}": val for i, val in enumerate(row)}

                row_data["target_section"] = "Others"
                extracted_rows.append(row_data)

        if extracted_rows:
            data["_rows"] = extracted_rows
            return data

        return {}
