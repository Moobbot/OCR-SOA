import os
import json
import glob
import pandas as pd

# from soa_extractor.rules import rule # Removed incorrect import

from soa_extractor.ocr_service import OCRService
from soa_extractor.llm.vllm_direct import VLLMDirectClient
from soa_extractor.pipeline.page_classifier import classify_page
from soa_extractor.pipeline.record_router import classify_record
from soa_extractor.pipeline.extractor import extract_records_batch
from soa_extractor.error_system import ERRORS, log_event

# validate_json is now used inside extractor, but imported for module consistency if needed


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_event(
            ERRORS.IO_READMD,
            f"Failed to read/parse JSON file: {path}",
            doc_id="sys",
            file=path,
            exc=e,
        )
        raise


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


def load_config(config_path="config.json"):
    """
    Loads configuration from a JSON file if it exists.
    Returns a dictionary of config values or empty dict.
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Warning: Failed to load {config_path}: {e}")
            return {}
    return {}


def main():
    # 1. Load Config
    config = load_config()

    # Top level config
    input_path = config.get("input")
    output_dir = config.get("output_dir", "outputs")

    # Nested configs with defaults
    llm_config = config.get("llm", {})
    llm_model = llm_config.get("model", "Qwen/Qwen2.5-14B-Instruct")
    llm_max_len = llm_config.get("max_model_len", 8192)
    llm_dtype = llm_config.get("dtype", "auto")

    ocr_config = config.get("ocr", {})
    ocr_model = ocr_config.get("model", "lightonai/LightOnOCR-2-1B")
    ocr_max_tokens = ocr_config.get("max_new_tokens", 8192)

    pipeline_config = config.get("pipeline", {})
    max_retries = pipeline_config.get("max_retries", 2)

    if not input_path:
        print("Error: 'input' must be defined in config.json")
        return

    print(f"Running SOA Extractor with config:")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  LLM: {llm_model} | MaxLen: {llm_max_len} | Dtype: {llm_dtype}")
    print(f"  OCR: {ocr_model}")
    print(f"  Pipeline Retries: {max_retries}")

    # 1. Setup Directories
    os.makedirs(output_dir, exist_ok=True)
    intermediate_dir = os.path.join("soa_extractor", "intermediate")
    os.makedirs(intermediate_dir, exist_ok=True)

    # SYSTEM LOGGING CONTEXT
    sys_ctx = {"doc_id": "sys", "file": "system"}

    # 2. Load Resources
    try:
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
    except Exception as e:
        log_event(
            ERRORS.SYS_CONFIG,
            "Failed to load configuration/resources",
            exc=e,
            **sys_ctx,
        )
        return

    # 3. Initialize Services
    try:
        ocr_service = OCRService(model_name=ocr_model, max_new_tokens=ocr_max_tokens)
        llm_client = VLLMDirectClient(
            model_name=llm_model, max_model_len=llm_max_len, dtype=llm_dtype
        )
    except Exception as e:
        log_event(ERRORS.SYS_DEP, "Failed to initialize services", exc=e, **sys_ctx)
        return

    # 4. Process Inputs
    input_files = []
    if os.path.isdir(input_path):
        input_files = glob.glob(os.path.join(input_path, "*.pdf"))
    else:
        input_files = [input_path]

    for pdf_file in input_files:
        print(f"Processing {pdf_file}...")
        base_name = os.path.splitext(os.path.basename(pdf_file))[0]
        final_results = []

        # File Context
        doc_id = base_name
        file_ctx = {"doc_id": doc_id, "file": base_name}

        try:
            # Loop over pages
            for page_num, markdown_text in ocr_service.process_pdf(pdf_file):
                print(f"  Page {page_num} extracted.")

                # Page Context
                page_ctx = {**file_ctx, "page": page_num}

                if not markdown_text.strip():
                    log_event(ERRORS.PAGE_HEADER, "Empty page content", **page_ctx)
                    continue

                # Save Intermediate
                try:
                    md_path = os.path.join(
                        intermediate_dir, f"{base_name}_page_{page_num}.md"
                    )
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(markdown_text)
                except Exception as e:
                    log_event(
                        ERRORS.IO_READMD,
                        "Failed to save intermediate markdown",
                        exc=e,
                        **page_ctx,
                    )

                # Classify Page
                page_type = classify_page(markdown_text, rules)
                print(f"  Page {page_num} classified as: {page_type}")

                if page_type == "Ignore":
                    log_event(
                        ERRORS.PAGE_CLASS,
                        "Page classified as Ignore",
                        level="INFO",
                        **page_ctx,
                    )
                    continue

                # Parse Records
                raw_records = parse_markdown_table_to_records(markdown_text)
                if not raw_records:
                    log_event(ERRORS.REC_EMPTY, "No records found on page", **page_ctx)
                    continue

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
                    else:
                        # Log Routing Error
                        log_event(
                            ERRORS.REC_ROUTE,
                            f"Could not route record: {record_text[:50]}...",
                            record_id=f"rec_{i}",
                            txn_type=txn_type,
                            **page_ctx,
                        )

                if not batch_data:
                    continue

                # Batch Extract with Retry & Logging
                print(f"    Extracting batch of {len(batch_data)} records...")
                validated_data_list = extract_records_batch(
                    batch_data,
                    llm_client,
                    prompt_template,
                    file_name=base_name,
                    start_record_id=0,  # In reality, accumulate this
                    max_retries=max_retries,
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
            try:
                output_json_path = os.path.join(output_dir, f"{base_name}.json")
                with open(output_json_path, "w", encoding="utf-8") as f:
                    json.dump(final_results, f, indent=2, ensure_ascii=False)
                print(f"Saved results to {output_json_path}")
            except Exception as e:
                log_event(
                    ERRORS.IO_WRITEJSON, "Failed to save JSON output", exc=e, **file_ctx
                )

            # Export to Excel
            if final_results:
                try:
                    df = pd.DataFrame(final_results)
                    output_excel_path = os.path.join(output_dir, f"{base_name}.xlsx")
                    df.to_excel(output_excel_path, index=False)
                    print(f"Saved results to {output_excel_path}")
                except Exception as e:
                    log_event(
                        ERRORS.IO_WRITECSV,
                        "Failed to save Excel output",
                        exc=e,
                        **file_ctx,
                    )

        except Exception as e:
            log_event(
                ERRORS.SYS_DEP,
                f"Unhandled error processing file {pdf_file}",
                exc=e,
                **file_ctx,
            )
            print(f"Error processing {pdf_file}: {e}")


if __name__ == "__main__":
    main()
