import json
from jinja2 import Template
from soa_extractor.pipeline.validator import validate_json
from soa_extractor.error_system import ERRORS, log_event


def build_prompt(
    group, txn_type, record_text, schema, template_content, error_msg=None
):
    template = Template(template_content)

    context_text = record_text
    if error_msg:
        context_text += f"\n\nPREVIOUS OUTPUT ERROR: {error_msg}\nPLEASE FIX THE JSON."

    prompt = template.render(
        GROUP=group,
        TXN_TYPE=txn_type,
        RECORD_TEXT=context_text,
        SCHEMA_JSON=json.dumps(schema, indent=2),
    )
    return prompt


def extract_records_batch(
    records_data,
    llm,
    prompt_template_content,
    file_name="unknown",
    start_record_id=0,
    max_retries=2,
):
    """
    Extracts a batch of records with self-healing (retry) logic and error logging.
    Returns a list of VALIDATED data dicts (or None if failed).
    """
    if not records_data:
        return []

    # Initialize results container
    # [ { 'status': 'pending', 'data': ..., 'retries': 0, 'last_error': None } ]
    results = [
        {"status": "pending", "data": None, "retries": 0, "last_error": None}
        for _ in records_data
    ]

    # We loop until all are done or max_retries reached
    current_retries = 0

    while current_retries <= max_retries:
        # 1. Identify items needing processing
        pending_indices = [i for i, r in enumerate(results) if r["status"] == "pending"]
        if not pending_indices:
            break

        print(
            f"    Batch processing: {len(pending_indices)} records (Attempt {current_retries + 1})"
        )

        # 2. Group by Schema for efficient batching
        schema_groups = {}
        for idx in pending_indices:
            item = records_data[idx]

            # Context for logging
            ctx_meta = {
                "file": file_name,
                "doc_id": file_name,  # Simplified for now
                "record_id": f"rec_{start_record_id + idx}",
                "group": item.get("group"),
                "txn_type": item.get("type"),
            }

            if not item.get("schema"):
                results[idx]["status"] = "failed"
                log_event(ERRORS.REC_ROUTE, "Missing schema for record", **ctx_meta)
                continue

            schema_str = json.dumps(item["schema"], sort_keys=True)
            if schema_str not in schema_groups:
                schema_groups[schema_str] = []

            # Build prompt with error history if any
            last_error = results[idx]["last_error"]
            prompt = build_prompt(
                group=item["group"],
                txn_type=item["type"],
                record_text=item["text"],
                schema=item["schema"],
                template_content=prompt_template_content,
                error_msg=last_error,
            )

            schema_groups[schema_str].append(
                {"original_index": idx, "prompt": prompt, "ctx_meta": ctx_meta}
            )

        # 3. Generate
        for schema_str, items in schema_groups.items():
            prompts = [item["prompt"] for item in items]

            outputs = []
            try:
                if hasattr(llm, "generate_batch_with_schema"):
                    outputs = llm.generate_batch_with_schema(prompts, schema_str)
                else:
                    if hasattr(llm, "generate_batch"):
                        outputs = llm.generate_batch(prompts)
                    else:
                        outputs = [llm.generate(p) for p in prompts]
            except Exception as e:
                # Log LLM error
                # We need to map exception to specific LLM error if possible
                err_code = ERRORS.LLM_RUNTIME
                if "out of memory" in str(e).lower():
                    err_code = ERRORS.LLM_OOM

                # Affects all items in this batch
                for item in items:
                    log_event(
                        err_code, "LLM generation failed", exc=e, **item["ctx_meta"]
                    )
                    # We might want to break or continue, here we assume it failed for this try
                    # Actually if LLM crashes, the whole script might crash unless caught here.
                    # append None outputs effectively
                    outputs.append(None)

                if len(outputs) < len(items):
                    outputs.extend([None] * (len(items) - len(outputs)))

            # 4. Validate and Update Status
            for item, raw_output in zip(items, outputs):
                idx = item["original_index"]
                target_schema = records_data[idx]["schema"]
                ctx_meta = item["ctx_meta"]

                if not raw_output:
                    log_event(ERRORS.LLM_EMPTY, "LLM returned empty output", **ctx_meta)
                    results[idx]["last_error"] = "Empty Output"
                    continue

                valid_data, error = validate_json(raw_output, target_schema)

                if valid_data:
                    results[idx]["status"] = "success"
                    results[idx]["data"] = valid_data
                    results[idx]["last_error"] = None
                else:
                    results[idx]["last_error"] = error

                    # Log validation error details
                    if "JSON Decode Error" in error:
                        log_event(ERRORS.LLM_JSONPARSE, error, **ctx_meta)
                    elif "Output is not a JSON object" in error:
                        log_event(ERRORS.LLM_NONJSON, error, **ctx_meta)
                    else:
                        # Schema validation errors (simplification)
                        log_event(ERRORS.VAL_SCHEMA, error, **ctx_meta)

                    # If this was the last retry, mark as failed
                    if current_retries == max_retries:
                        results[idx]["status"] = "failed"
                        log_event(
                            ERRORS.LLM_RETRY,
                            f"Max retries reached. Last error: {error}",
                            **ctx_meta,
                        )

        current_retries += 1

    # Extract final data
    final_output = []
    for r in results:
        if r["status"] == "success":
            final_output.append(r["data"])
        else:
            final_output.append(None)

    return final_output
