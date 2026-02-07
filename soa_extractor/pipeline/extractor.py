import json
from jinja2 import Template
from soa_extractor.pipeline.validator import validate_json


def build_prompt(
    group, txn_type, record_text, schema, template_content, error_msg=None
):
    template = Template(template_content)
    # If error_msg is present, we might want to append it to the prompt or use a different template
    # For now, let's just append it to the record text or add a specific section

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


def extract_records_batch(records_data, llm, prompt_template_content, max_retries=2):
    """
    Extracts a batch of records with self-healing (retry) logic.
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
            if not item.get("schema"):
                results[idx]["status"] = "failed"
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

            schema_groups[schema_str].append({"original_index": idx, "prompt": prompt})

        # 3. Generate
        for schema_str, items in schema_groups.items():
            prompts = [item["prompt"] for item in items]

            if hasattr(llm, "generate_batch_with_schema"):
                outputs = llm.generate_batch_with_schema(prompts, schema_str)
            else:
                if hasattr(llm, "generate_batch"):
                    outputs = llm.generate_batch(prompts)
                else:
                    outputs = [llm.generate(p) for p in prompts]

            # 4. Validate and Update Status
            for item, raw_output in zip(items, outputs):
                idx = item["original_index"]
                target_schema = records_data[idx]["schema"]

                valid_data, error = validate_json(raw_output, target_schema)

                if valid_data:
                    results[idx]["status"] = "success"
                    results[idx]["data"] = valid_data
                    results[idx]["last_error"] = None
                else:
                    results[idx]["last_error"] = error
                    # If we have retries left, verify status remains pending
                    # If this was the last retry, mark as failed
                    if current_retries == max_retries:
                        results[idx]["status"] = "failed"

        current_retries += 1

    # Extract final data
    final_output = []
    for r in results:
        if r["status"] == "success":
            final_output.append(r["data"])
        else:
            final_output.append(None)  # Or return partial error info?
            if r["last_error"]:
                print(
                    f"    Failed to extract record after retries. Error: {r['last_error']}"
                )

    return final_output
