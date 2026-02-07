import os
import json
import argparse
import glob
import pandas as pd

# from soa_extractor.rules import rule # Removed incorrect import

from soa_extractor.ocr_service import OCRService
from soa_extractor.llm.vllm_direct import VLLMDirectClient
from soa_extractor.pipeline.page_classifier import classify_page
from soa_extractor.pipeline.record_router import classify_record
from soa_extractor.pipeline.extractor import extract_records_batch


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_markdown_table_to_records(markdown_text):
    """
    Simple parser to extract rows from markdown tables.
    """
    records = []
    lines = markdown_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if "---" in stripped:
                continue
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
        "Others": load_json_file(os.path.join(schemas_dir, "others.json")),
    }

    prompt_path = os.path.join(base_dir, "prompts", "extract_record.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # 3. Initialize Services
    ocr_service = OCRService()

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
            # Loop over pages
            for page_num, markdown_text in ocr_service.process_pdf(pdf_file):
                print(f"  Page {page_num} extracted.")

                # Save Intermediate
                md_path = os.path.join(
                    intermediate_dir, f"{base_name}_page_{page_num}.md"
                )
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(markdown_text)

                # Classify Page
                page_type = classify_page(markdown_text, rules)
                print(f"  Page {page_num} classified as: {page_type}")

                if page_type == "Ignore":
                    continue

                # Parse Records
                raw_records = parse_markdown_table_to_records(markdown_text)
                print(f"  Found {len(raw_records)} potential records.")

                # Prepare Batch
                batch_data = []
                for i, record_text in enumerate(raw_records):
                    txn_group, txn_type = classify_record(record_text, rules)
                    target_schema = schemas.get(txn_group)

                    if target_schema:
                        batch_data.append(
                            {
                                "text": record_text,
                                "group": txn_group,
                                "type": txn_type,
                                "schema": target_schema,
                                "original_index": i,
                            }
                        )

                if not batch_data:
                    continue

                # Batch Extract with Retry
                # Now returns validated dicts directly
                print(f"    Extracting batch of {len(batch_data)} records...")
                validated_data_list = extract_records_batch(
                    batch_data, llm_client, prompt_template
                )

                # Collect
                for item, data in zip(batch_data, validated_data_list):
                    if data:
                        data["_meta"] = {
                            "page": page_num,
                            "group": item["group"],
                            "type": item["type"],
                            "source_file": base_name,
                        }
                        final_results.append(data)

            # Save Final Output
            output_json_path = os.path.join(args.output_dir, f"{base_name}.json")
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
            print(f"Saved results to {output_json_path}")

            # Export to Excel
            if final_results:
                df = pd.DataFrame(final_results)
                output_excel_path = os.path.join(args.output_dir, f"{base_name}.xlsx")
                df.to_excel(output_excel_path, index=False)
                print(f"Saved results to {output_excel_path}")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")


if __name__ == "__main__":
    main()
