**Bộ mã lỗi (error code set) + format log chuẩn** để nhúng vào pipeline **SOA: Markdown → rule page → rule routing → LLM extract → validate → output**. Mục tiêu: **theo dõi chính xác**, debug nhanh, thống kê được theo loại lỗi.

---

## 1) Quy ước mã lỗi

**Format:** `SOA-<TẦNG>-<NHÓM>-<SỐ>`

- `TẦNG`: `PAGE`, `REC`, `LLM`, `VAL`, `IO`, `SYS`
- `NHÓM`: ngắn gọn theo chức năng
- `SỐ`: 3 chữ số

Ví dụ: `SOA-LLM-TIMEOUT-001`

---

## 2) Danh mục mã lỗi đề xuất

### A. PAGE — lỗi cấp trang

- `SOA-PAGE-HEADER-001` — Không đọc được header (md trống / lỗi parse)
- `SOA-PAGE-CLASS-002` — Không match được loại trang (không phải Positions/Transaction → Ignore)
- `SOA-PAGE-SPLIT-003` — Lỗi tách page/chunk (marker thiếu, page merge sai)

### B. REC — lỗi cấp record (giao dịch)

- `SOA-REC-EMPTY-001` — Record rỗng sau khi parse
- `SOA-REC-STITCH-002` — Lỗi stitch dòng (row broken không ghép được)
- `SOA-REC-ROUTE-003` — Không route được group (FXTX/Other/Trade) theo rule
- `SOA-REC-DUP-004` — Record nghi trùng (hash trùng trong cùng page)
- `SOA-REC-NOISE-005` — Record bị nhiễu OCR quá mức (tỉ lệ ký tự lạ vượt ngưỡng)

### C. LLM — lỗi gọi model local / sinh output

- `SOA-LLM-OOM-001` — GPU OOM / CUDA out of memory
- `SOA-LLM-TIMEOUT-002` — Quá thời gian generate
- `SOA-LLM-RUNTIME-003` — Lỗi runtime vLLM/transformers (engine crash)
- `SOA-LLM-EMPTY-004` — Model trả output rỗng
- `SOA-LLM-NONJSON-005` — Output không phải JSON
- `SOA-LLM-JSONPARSE-006` — JSON parse fail (trailing text, invalid commas…)
- `SOA-LLM-HALLU-007` — Output có field “bịa” (không trong schema) hoặc thay đổi txn_type text
- `SOA-LLM-RETRY-008` — Đã retry vượt ngưỡng cho record

### D. VAL — lỗi validate/normalize

- `SOA-VAL-SCHEMA-001` — Thiếu field bắt buộc / schema mismatch
- `SOA-VAL-DATE-002` — Date parse fail
- `SOA-VAL-CURR-003` — Currency không nằm trong enum
- `SOA-VAL-ISIN-004` — ISIN invalid (regex/length)
- `SOA-VAL-NUM-005` — Number parse fail (1,2.. / parentheses)
- `SOA-VAL-RANGE-006` — Value ngoài range (quantity <0, decimals vượt giới hạn)
- `SOA-VAL-CONFLICT-007` — Mâu thuẫn logic (FXTX nhưng thiếu Currency Buy/Sell, v.v.)

### E. IO — lỗi đọc/ghi

- `SOA-IO-READMD-001` — Đọc file md lỗi
- `SOA-IO-WRITEJSON-002` — Ghi JSON output lỗi
- `SOA-IO-WRITECSV-003` — Ghi CSV lỗi
- `SOA-IO-ENC-004` — Encoding lỗi (UTF-8 decode)

### F. SYS — lỗi hệ thống

- `SOA-SYS-CONFIG-001` — Thiếu config (đường dẫn model, schema, rule)
- `SOA-SYS-VERSION-002` — Model/tokenizer mismatch version
- `SOA-SYS-DEP-003` — Thiếu dependency / import error

---

## 3) Chuẩn event log (để theo dõi “chuẩn xác”)

Mỗi lỗi log theo JSON line (1 dòng = 1 event) để dễ ingest vào ELK/Grafana:

```json
{
  "ts": "2026-02-07T12:34:56.123+07:00",
  "level": "ERROR",
  "code": "SOA-LLM-NONJSON-005",
  "stage": "llm_extract",
  "doc_id": "batch_20260207_001",
  "file": "abc_soa_01.md",
  "page": 3,
  "record_id": "p3_r12",
  "group": "Trade",
  "txn_type": "REPAYMENT",
  "message": "Model output is not valid JSON",
  "meta": {
    "model": "Qwen/Qwen2.5-14B-Instruct",
    "max_tokens": 1024,
    "retry": 1
  }
}
```

---

## 4) Code mẫu để nhúng (Python) — dùng luôn được

### 4.1. Enum error codes

```python
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import traceback
from typing import Any, Optional, Dict

@dataclass(frozen=True)
class Err:
    code: str
    stage: str
    level: str = "ERROR"

class ERRORS:
    # PAGE
    PAGE_HEADER = Err("SOA-PAGE-HEADER-001", "page_parse")
    PAGE_CLASS  = Err("SOA-PAGE-CLASS-002", "page_classify")
    PAGE_SPLIT  = Err("SOA-PAGE-SPLIT-003", "page_split")

    # REC
    REC_EMPTY   = Err("SOA-REC-EMPTY-001", "record_parse")
    REC_STITCH  = Err("SOA-REC-STITCH-002", "record_stitch")
    REC_ROUTE   = Err("SOA-REC-ROUTE-003", "record_route")
    REC_DUP     = Err("SOA-REC-DUP-004", "record_dedup")
    REC_NOISE   = Err("SOA-REC-NOISE-005", "record_quality")

    # LLM
    LLM_OOM     = Err("SOA-LLM-OOM-001", "llm_extract")
    LLM_TIMEOUT = Err("SOA-LLM-TIMEOUT-002", "llm_extract")
    LLM_RUNTIME = Err("SOA-LLM-RUNTIME-003", "llm_extract")
    LLM_EMPTY   = Err("SOA-LLM-EMPTY-004", "llm_extract")
    LLM_NONJSON = Err("SOA-LLM-NONJSON-005", "llm_parse")
    LLM_JSONPARSE=Err("SOA-LLM-JSONPARSE-006","llm_parse")
    LLM_HALLU   = Err("SOA-LLM-HALLU-007", "llm_validate")
    LLM_RETRY   = Err("SOA-LLM-RETRY-008", "llm_extract")

    # VAL
    VAL_SCHEMA  = Err("SOA-VAL-SCHEMA-001", "validate")
    VAL_DATE    = Err("SOA-VAL-DATE-002", "validate")
    VAL_CURR    = Err("SOA-VAL-CURR-003", "validate")
    VAL_ISIN    = Err("SOA-VAL-ISIN-004", "validate")
    VAL_NUM     = Err("SOA-VAL-NUM-005", "validate")
    VAL_RANGE   = Err("SOA-VAL-RANGE-006", "validate")
    VAL_CONFLICT= Err("SOA-VAL-CONFLICT-007","validate")

    # IO
    IO_READMD   = Err("SOA-IO-READMD-001", "io")
    IO_WRITEJSON= Err("SOA-IO-WRITEJSON-002", "io")
    IO_WRITECSV = Err("SOA-IO-WRITECSV-003", "io")
    IO_ENC      = Err("SOA-IO-ENC-004", "io")

    # SYS
    SYS_CONFIG  = Err("SOA-SYS-CONFIG-001", "startup")
    SYS_VERSION = Err("SOA-SYS-VERSION-002", "startup")
    SYS_DEP     = Err("SOA-SYS-DEP-003", "startup")
```

### 4.2. Logger JSONL

```python
def now_iso():
    # timezone aware ISO (you can set +07:00 if needed)
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")

def log_event(
    err: Err,
    message: str,
    doc_id: str,
    file: str,
    page: Optional[int] = None,
    record_id: Optional[str] = None,
    group: Optional[str] = None,
    txn_type: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    exc: Optional[BaseException] = None,
    level: Optional[str] = None
):
    event = {
        "ts": now_iso(),
        "level": level or err.level,
        "code": err.code,
        "stage": err.stage,
        "doc_id": doc_id,
        "file": file,
        "page": page,
        "record_id": record_id,
        "group": group,
        "txn_type": txn_type,
        "message": message,
        "meta": meta or {}
    }
    if exc is not None:
        event["meta"]["exception"] = str(exc)
        event["meta"]["trace"] = traceback.format_exc(limit=5)

    print(json.dumps(event, ensure_ascii=False))
```

### 4.3. Ví dụ dùng trong pipeline

```python
def safe_llm_extract(llm, prompt, ctx):
    try:
        out = llm.generate(prompt)
        if not out or not out.strip():
            log_event(ERRORS.LLM_EMPTY, "Empty LLM output", **ctx)
            return None
        return out
    except RuntimeError as e:
        # crude OOM detection
        if "out of memory" in str(e).lower():
            log_event(ERRORS.LLM_OOM, "CUDA OOM during LLM generate", exc=e, **ctx)
        else:
            log_event(ERRORS.LLM_RUNTIME, "RuntimeError during LLM generate", exc=e, **ctx)
        return None
```

---

## 5) “Bảng mapping nhanh” để bạn đưa vào tài liệu

- Page-level:
  - header trống → `SOA-PAGE-HEADER-001`
  - không match Positions/Transaction → `SOA-PAGE-CLASS-002`

- Record-level:
  - record rỗng → `SOA-REC-EMPTY-001`
  - route fail → `SOA-REC-ROUTE-003`

- LLM:
  - OOM → `SOA-LLM-OOM-001`
  - non-json → `SOA-LLM-NONJSON-005`
  - schema mismatch → `SOA-VAL-SCHEMA-001`

---
