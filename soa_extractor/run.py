import os
import json
import argparse
import glob

# from soa_extractor.rules import rule # Removed incorrect import

# Since rule.json is a json file, we load it using json module, not import
# We will load it in main

from soa_extractor.ocr_service import OCRService
from soa_extractor.llm.vllm_direct import VLLMDirectClient
from soa_extractor.pipeline.page_classifier import classify_page
from soa_extractor.pipeline.record_router import classify_record
from soa_extractor.pipeline.extractor import extract_record
from soa_extractor.pipeline.validator import validate_json


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_markdown_table_to_records(markdown_text):
    """
    Simple parser to extract rows from markdown tables.
    Returns a list of strings, where each string is a row in markdown format.
    """
    records = []
    lines = markdown_text.split("\n")
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            # It's a table row
            # Skip separator lines like |---|---|
            if "---" in stripped:
                continue
            # Skip header row? Maybe not, header might help context, but usually we process data rows
            # For simplicity, we treat every row as a potential record.
            # Page classifier should tell us if this page is relevant first.
            records.append(stripped)

    return records


def main():
    parser = argparse.ArgumentParser(description="SOA Extractor Pipeline")
    parser.add_argument("--input", required=True, help="Input PDF file or directory")
    parser.add_argument(
        "--model", default="Qwen/Qwen2.5-14B-Instruct", help="LLM Model name"
    )
    parser.add_argument("--output_dir", default="outputs", help="Output directory")

    args = parser.parse_args()

    # 1. Setup Directories
    os.makedirs(args.output_dir, exist_ok=True)
    intermediate_dir = os.path.join("soa_extractor", "intermediate")
    os.makedirs(intermediate_dir, exist_ok=True)

    # 2. Load Resources
    base_dir = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(base_dir, "rules", "rule.json")
    rules = load_json_file(rules_path)

    schemas_dir = os.path.join(base_dir, "schemas")
    schemas = {
        "Trade": load_json_file(os.path.join(schemas_dir, "trade.json")),
        "FXTF": load_json_file(os.path.join(schemas_dir, "fxtx.json")),
        "Positions": load_json_file(os.path.join(schemas_dir, "positions.json")),
        # Add others if needed
    }

    prompt_path = os.path.join(base_dir, "prompts", "extract_record.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # 3. Initialize Services
    ocr_service = OCRService()  # Lazy loads model

    # Note: VLLM client initialization might fail if no GPU/vLLM installed.
    # Ensure environment is ready.
    try:
        llm_client = VLLMDirectClient(model_name=args.model)
    except Exception as e:
        print(f"Error initializing LLM Client: {e}")
        return

    # 4. Process Inputs
    input_files = []
    if os.path.isdir(args.input):
        input_files = glob.glob(os.path.join(args.input, "*.pdf"))
    else:
        input_files = [args.input]

    for pdf_file in input_files:
        print(f"Processing {pdf_file}...")
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        final_results = []

        try:
            # OCR Layer
            for page_num, markdown_text in ocr_service.process_pdf(pdf_file):
                print(f"  Page {page_num} extracted.")

                # Save Intermediate Markdown
                md_path = os.path.join(
                    intermediate_dir, f"{base_name}_page_{page_num}.md"
                )
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(markdown_text)

                # Classification Layer
                page_type = classify_page(markdown_text, rules)
                print(f"  Page {page_num} classified as: {page_type}")

                if page_type == "Ignore":
                    continue

                # Routing & Extraction Layer
                records = parse_markdown_table_to_records(markdown_text)
                print(f"  Found {len(records)} potential records.")

                for i, record_text in enumerate(records):
                    # Route
                    txn_group, txn_type = classify_record(record_text, rules)

                    # Skip 'Other' if we want strictly matched transactions
                    # Or map 'Other' to a generic schema?
                    # For now, if output_group is 'Others' and we don't have schema, skip or use trade?
                    # rule.json defines 'Others' group.

                    target_schema = schemas.get(txn_group)
                    if not target_schema:
                        # Fallback or skip
                        continue

                    # Extract
                    print(f"    Extracting record {i+1} as {txn_group}/{txn_type}...")
                    raw_json = extract_record(
                        record_text=record_text,
                        group=txn_group,
                        txn_type=txn_type,
                        llm=llm_client,
                        schema=target_schema,
                        prompt_template_content=prompt_template,
                    )

                    # Validate
                    data, error = validate_json(raw_json, target_schema)
                    if data:
                        data["_meta"] = {
                            "page": page_num,
                            "group": txn_group,
                            "type": txn_type,
                            "source_file": base_name,
                        }
                        final_results.append(data)
                    else:
                        print(f"    Validation failed: {error}")

            # Save Final Output
            output_json_path = os.path.join(args.output_dir, f"{base_name}.json")
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
            print(f"Saved results to {output_json_path}")

            # Export to Excel
            if final_results:
                import pandas as pd

                df = pd.DataFrame(final_results)
                output_excel_path = os.path.join(args.output_dir, f"{base_name}.xlsx")
                df.to_excel(output_excel_path, index=False)
                print(f"Saved results to {output_excel_path}")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")


if __name__ == "__main__":
    main()
