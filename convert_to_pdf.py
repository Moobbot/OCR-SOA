import markdown
from xhtml2pdf import pisa
import os
import requests
import re
import pathlib


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


def convert_md_to_pdf(md_file, pdf_file):
    # 1. Read Markdown file
    with open(md_file, "r", encoding="utf-8") as f:
        text = f.read()

    # 2. Convert to HTML
    html_content = markdown.markdown(text, extensions=["tables", "fenced_code"])

    # 3. Inject custom class and colgroup for "Extraction Rules & Constraints" tables
    # Identify tables where the first header is "Field" and inject colgroup
    # Identify tables where the first header is "Field" and inject colgroup
    html_content = re.sub(
        r"<table>(\s*<thead>\s*<tr>\s*<th[^>]*>Field</th>)",
        r"""<table class="constraints-table">
            <colgroup>
                <col width="15%">
                <col width="25%">
                <col width="60%">
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
        
        /* Specific column widths for Constraints table (backup to colgroup) */
        .constraints-table th:nth-child(1), .constraints-table td:nth-child(1) {{ width: 15%; }}
        .constraints-table th:nth-child(2), .constraints-table td:nth-child(2) {{ width: 25%; }}
        .constraints-table th:nth-child(3), .constraints-table td:nth-child(3) {{ width: 60%; }}
    </style>
    """

    full_html = f"<html><head>{css}</head><body>{html_content}</body></html>"

    # 5. Write PDF
    with open(pdf_file, "wb") as result_file:
        pisa_status = pisa.CreatePDF(full_html, dest=result_file, encoding="utf-8")

    if pisa_status.err:
        print(f"Error converting to PDF: {pisa_status.err}")
    else:
        print(f"Successfully created PDF: {pdf_file}")


if __name__ == "__main__":
    # Use absolute paths for stability or relative if running from root
    input_md = (
        r"d:\Work\Clients\AIRC\product\ACPA\LightOnOCR-2-1B-Demo\rule_analysis.md"
    )
    output_pdf = (
        r"d:\Work\Clients\AIRC\product\ACPA\LightOnOCR-2-1B-Demo\rule_analysis.pdf"
    )

    convert_md_to_pdf(input_md, output_pdf)
