import json
from jinja2 import Template


def build_prompt(group, txn_type, record_text, schema, template_content):
    template = Template(template_content)
    prompt = template.render(
        GROUP=group,
        TXN_TYPE=txn_type,
        RECORD_TEXT=record_text,
        SCHEMA_JSON=json.dumps(schema, indent=2),
    )
    return prompt


def extract_record(record_text, group, txn_type, llm, schema, prompt_template_content):
    """
    Extracts data from a record using values.
    """
    prompt = build_prompt(
        group=group,
        txn_type=txn_type,
        record_text=record_text,
        schema=schema,
        template_content=prompt_template_content,
    )

    raw_response = llm.generate(prompt)
    return raw_response
