**1 khung chung (framework/template)**, để **chạy riêng 3 model**:

- Qwen2.5-14B-Instruct
- Qwen2.5-7B-Instruct
- DeepSeek-V3 (32B)

👉 **Chỉ swap model**, **không đổi pipeline / prompt / schema**, **truyền prompt thẳng vào model local**.

Dưới đây là **khung chuẩn – production-style – đúng triết lý rule-first của bạn**.

---

# 1️⃣ Kiến trúc tổng thể (KHUNG CHUNG)

```
┌──────────────┐
│ PDF          │
└──────┬───────┘
       ↓
┌──────────────┐
│ LightOnOCR   │
│ → Markdown   │
└──────┬───────┘
       ↓
┌──────────────────────────┐
│ Rule Engine (NO LLM)     │
│ - Page classification    │
│ - Record routing         │
└──────┬───────────────────┘
       ↓
┌──────────────────────────┐
│ LLM Adapter (SWAPPABLE)  │◄──────┐
│ - Prompt builder         │       │
│ - Schema injection       │       │
│ - Direct inference       │       │
└──────┬───────────────────┘       │
       ↓                           │
┌──────────────────────────┐       │
│ Output: EXCEL            │       │
└──────────────────────────┘       │
        ┌──────────────────────────┴─────────────┐
        │   Qwen2.5-7B | Qwen2.5-14B | DeepSeek  │
        └────────────────────────────────────────┘
```

---

# 2️⃣ Folder structure (rất nên giữ)

```
soa_extractor/
│
├── rules/
│   └── rule.json
│
├── schemas/
│   ├── trade.json
│   ├── fxtx.json
│   └── positions.json
│
├── prompts/
│   └── extract_record.txt
│
├── llm/
│   ├── base.py              # interface
│   ├── vllm_direct.py       # direct inference bằng vLLM  dùng cho (khuyến nghị)
│
├── pipeline/
│   ├── page_classifier.py
│   ├── record_router.py
│   ├── extractor.py
│   └── validator.py
│
└── run.py
```

---

# 3️⃣ Chuẩn hoá Interface LLM (CỐT LÕI)

### `llm/base.py`

```python
class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
```

---

# 4️⃣ LLM Adapter chạy “truyền thẳng” (KHÔNG server)

## ✅ Khuyến nghị: vLLM direct (nhanh, batch tốt)

### `llm/vllm_direct.py`

```python
from vllm import LLM, SamplingParams
from llm.base import LLMClient

class VLLMDirectClient(LLMClient):
    def __init__(
        self,
        model_name: str,
        max_model_len: int = 8192,
        dtype: str = "auto"
    ):
        self.model_name = model_name
        self.llm = LLM(model=model_name, dtype=dtype, max_model_len=max_model_len)
        self.sampling = SamplingParams(temperature=0, top_p=1, max_tokens=1024)

    def generate(self, prompt: str) -> str:
        outputs = self.llm.generate([prompt], self.sampling)
        return outputs[0].outputs[0].text
```

👉 **Đoạn này KHÔNG đổi cho 3 model** (chỉ đổi `model_name`).

---

# 5️⃣ Prompt chung (KHÔNG model-specific)

### `prompts/extract_record.txt`

```text
You are a financial data extraction engine.

Rules:
- Page classification and transaction routing are already done.
- DO NOT classify or infer.
- DO NOT change transaction type text.
- If a field is missing, return null.
- Output MUST be valid JSON and follow schema strictly.

Transaction group: {{GROUP}}
Transaction type: {{TXN_TYPE}}

Input record:
---
{{RECORD_TEXT}}
---

Return JSON only.
Schema:
{{SCHEMA_JSON}}
```

👉 Prompt này chạy **nguyên xi** cho cả 3 model.

---

# 6️⃣ Record-level extractor (logic chung)

### `pipeline/extractor.py`

```python
def extract_record(record, llm, schema):
    prompt = build_prompt(
        group=record.group,
        txn_type=record.txn_type,
        record_text=record.text,
        schema=schema
    )
    raw = llm.generate(prompt)
    return validate_json(raw, schema)
```

---

# 7️⃣ Chạy RIÊNG từng model (chỉ đổi model_name)

## 🟢 A. Qwen2.5-7B-Instruct

```python
llm = VLLMDirectClient("Qwen/Qwen2.5-7B-Instruct")
```

---

## 🟢 B. Qwen2.5-14B-Instruct (recommended)

```python
llm = VLLMDirectClient("Qwen/Qwen2.5-14B-Instruct")
```

---

## 🔵 C. DeepSeek-V3 (32B)

```python
llm = VLLMDirectClient("deepseek-ai/DeepSeek-V3")
```

👉 **Không cần chạy server**, **không đổi pipeline/prompt/schema**.

---

# 8️⃣ Điểm quan trọng để 3 model cho kết quả gần nhau

| Biện pháp          | Bắt buộc |
| ------------------ | -------- |
| temperature = 0    | ✅       |
| record context nhỏ | ✅       |
| schema strict      | ✅       |
| rule routing trước | ✅       |
| validator sau LLM  | ✅       |
