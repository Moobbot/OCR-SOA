import markdown
import os
import requests
import re
import pathlib
import json


def download_font(font_path):
    if not os.path.exists(font_path):
        print("Downloading font supporting Vietnamese...")
        url = (
            "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
        )
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
        print("Font downloaded.")


def generate_markdown_from_json(json_data):
    md_lines = []

    md_lines.append("# Extraction Rules Analysis")
    md_lines.append("")

    # Process Sections
    if "sections" in json_data:
        for section in json_data["sections"]:
            md_lines.append(
                f"## Section {section.get('section_id')}: {section.get('section_name')}"
            )
            md_lines.append("")

            # Columns Table
            if "columns" in section:
                md_lines.append("### Columns")
                md_lines.append("| Index | Name | Format |")
                md_lines.append("| --- | --- | --- |")
                for col in section["columns"]:
                    md_lines.append(
                        f"| {col.get('index')} | {col.get('name')} | {col.get('format')} |"
                    )
                md_lines.append("")

            # Extraction Rules
            if "extraction_rules" in section:
                md_lines.append("### Extraction Rules")
                md_lines.append("| Field | Source | Logic/Details | Constraints |")
                md_lines.append("| --- | --- | --- | --- |")

                for field, rule in section["extraction_rules"].items():
                    source = rule.get("source", "")
                    if isinstance(source, list):
                        source = ", ".join(source)
                    elif isinstance(source, dict):
                        source = "<br>".join([f"{k}: {v}" for k, v in source.items()])

                    logic = []
                    if "logic" in rule:
                        logic.append(f"Logic: {rule['logic']}")
                    if "regex" in rule:
                        logic.append(f"Regex: `{rule['regex']}`")
                    if "classifier" in rule:
                        logic.append(f"Classifier: {rule['classifier']}")
                    if "description" in rule:
                        logic.append(f"Desc: {rule['description']}")
                    if "keywords" in rule:
                        logic.append(f"Keywords: {', '.join(rule['keywords'])}")

                    logic_str = "<br>".join(logic)

                    constraints = rule.get("constraints", [])
                    constraints_str = "<br>".join(constraints) if constraints else ""

                    md_lines.append(
                        f"| {field} | {source} | {logic_str} | {constraints_str} |"
                    )
                md_lines.append("")

    # Transaction Type Rules
    if "transaction_type_rules" in json_data:
        md_lines.append("## Transaction Type Rules")
        md_lines.append("| Name | Priority | Match Any | Output |")
        md_lines.append("| --- | --- | --- | --- |")
        for rule in json_data["transaction_type_rules"]:
            match_any = ", ".join(rule.get("match_any", []))
            if rule.get("fallback"):
                match_any = "(Fallback)"
            md_lines.append(
                f"| {rule.get('name')} | {rule.get('priority', 0)} | {match_any} | {rule.get('output')} |"
            )
        md_lines.append("")

    # Global Field Constraints
    if "global_field_constraints" in json_data:
        md_lines.append("## Global Field Constraints")
        md_lines.append("| Field Name | Constraints / Mappings |")
        md_lines.append("| --- | --- |")
        for item in json_data["global_field_constraints"]:
            content = []
            if "constraints" in item:
                content.extend(item["constraints"])
            if "mappings" in item:
                content.append(f"Mappings: {json.dumps(item['mappings'])}")

            content_str = "<br>".join(content)
            md_lines.append(f"| {item.get('field_name')} | {content_str} |")
        md_lines.append("")

    return "\n".join(md_lines)


def convert_md_to_html(md_content, html_file):
    # 2. Convert to HTML
    html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    # 3. Inject custom class and colgroup for "Extraction Rules & Constraints" tables
    # Identify tables where the first header is "Field" and inject colgroup
    html_content = re.sub(
        r"<table>(\s*<thead>\s*<tr>\s*<th[^>]*>Field</th>)",
        r"""<table class="constraints-table">
            <colgroup>
                <col width="20%">
                <col width="20%">
                <col width="30%">
                <col width="30%">
            </colgroup>\1""",
        html_content,
    )

    # 4. Prepare CSS for Font handling
    font_path = "Roboto-Regular.ttf"
    download_font(font_path)

    # Use standard library to get proper file URI
    abs_font_path = pathlib.Path(font_path).absolute().as_uri()

    # Check if download was successful
    if not os.path.exists(font_path):
        print(f"Failed to find font file at {abs_font_path}")
        return

    css = f"""
    <style>
        @font-face {{
            font-family: 'Roboto';
            src: url('{abs_font_path}');
        }}
        body {{
            font-family: 'Roboto', sans-serif;
            font-size: 10pt;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
            table-layout: fixed;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            word-wrap: break-word;
            vertical-align: top;
            white-space: normal;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        
        /* Specific column widths for Extraction Rules table */
        .constraints-table th:nth-child(1), .constraints-table td:nth-child(1) {{ width: 20%; }}
        .constraints-table th:nth-child(2), .constraints-table td:nth-child(2) {{ width: 20%; }}
        .constraints-table th:nth-child(3), .constraints-table td:nth-child(3) {{ width: 30%; }}
        .constraints-table th:nth-child(4), .constraints-table td:nth-child(4) {{ width: 30%; }}
    </style>
    """

    full_html = f"<html><head>{css}</head><body>{html_content}</body></html>"

    # Save HTML
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"HTML saved to: {html_file}")


if __name__ == "__main__":
    # Use absolute paths for stability or relative if running from root
    base_dir = r"d:\Work\Clients\AIRC\product\ACPA\LightOnOCR-2-1B-Demo"
    input_json = os.path.join(base_dir, "docs", "rule.json")
    output_html = os.path.join(base_dir, "docs", "rule_analysis.html")

    # Generate Markdown from JSON
    if os.path.exists(input_json):
        with open(input_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        md_content = generate_markdown_from_json(data)

        # Save MD for reference
        md_file = input_json.replace(".json", ".md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"Generated Markdown saved to: {md_file}")

        convert_md_to_html(md_content, output_html)
    else:
        print(f"Error: {input_json} not found.")
