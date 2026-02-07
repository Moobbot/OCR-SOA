# SOA Extractor Architecture

This repository implements a modular, service-oriented architecture (SOA) for extracting financial data from PDF documents using LightOnOCR and LLMs (Qwen/DeepSeek).

## Architecture Overview

The system follows a strict pipeline:

1.  **OCR**: Converts PDF/Image to Markdown using `LightOnOCR-2-1B`.
2.  **Intermediate Storage**: Saves the raw Markdown to `soa_extractor/intermediate/`.
3.  **Rule Engine (NO LLM)**:
    - **Page Classification**: Determines if a page contains Trade, FX, Position, or other data based on keywords/headers.
    - **Record Routing**: Splits the markdown into records (lines/rows) and classifies each record into a Transaction Group and Type.
4.  **Extraction (LLM)**:
    - Uses a **Swappable LLM Adapter** (vLLM recommended) to extract structured data from each record.
    - Injects a strict JSON schema and specific prompt into the LLM.
5.  **Validation**: Validates the LLM output against the schema.

## Directory Structure

```
soa_extractor/
├── rules/
│   └── rule.json          # Configuration for classification and routing
├── schemas/               # JSON Schemas for each transaction group
│   ├── trade.json
│   ├── fxtx.json
│   └── positions.json
├── prompts/
│   └── extract_record.txt # Jinja2 template for LLM prompting
├── llm/
│   ├── base.py            # LLM Client Interface
│   └── vllm_direct.py     # vLLM Implementation (High Performance)
├── pipeline/
│   ├── page_classifier.py # Rule-based page classification
│   ├── record_router.py   # Rule-based record routing
│   ├── extractor.py       # Orchestrates Prompt + LLM
│   └── validator.py       # JSON Validation
├── intermediate/          # Stores extracted Markdown files
├── ocr_service.py         # Wrapper for LightOnOCR
└── run.py                 # Main entry point
```

## Setup

1.  **Dependencies**: Ensure you have `vllm`, `transformers`, `torch`, `pypdfium2`, `jinja2` installed.
    - Note: `vllm` runs best on Linux with CUDA. For Windows, you might need WSL2 or replace `vllm_direct.py` with an OpenAI-compatible adapter if running a local server.

2.  **Models**:
    - OCR: `lightonai/LightOnOCR-2-1B` (Downloaded automatically by transformers).
    - Extraction: `Qwen/Qwen2.5-14B-Instruct` (or 7B, or DeepSeek-V3).

## Usage

Run the extraction pipeline:

```bash
python -m soa_extractor.run --input path/to/document.pdf --model Qwen/Qwen2.5-14B-Instruct
```

### Output

- **Intermediate Markdown**: Saved in `soa_extractor/intermediate/`.
- **Final JSON**: Saved in `outputs/`.

## Customization

- **Rules**: Edit `soa_extractor/rules/rule.json` to change classification keywords.
- **Schemas**: Edit `soa_extractor/schemas/*.json` to change output fields.
- **Prompt**: Edit `soa_extractor/prompts/extract_record.txt` to change instructions.
