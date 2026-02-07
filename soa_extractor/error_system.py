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
    
    # In a real system, you might write this to a file or send to ELK
    print(json.dumps(event, ensure_ascii=False))
