"""Data ingestion: files, REST APIs and SQL databases."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from modules.sql_safety import validate_sql

SUPPORTED = {".csv", ".tsv", ".xlsx", ".xls", ".json"}


def load_file(file_or_path, filename: str | None = None, sheet_name=0) -> pd.DataFrame:
    """Load CSV / TSV / Excel / JSON from a path or a Streamlit UploadedFile."""
    name = filename or getattr(file_or_path, "name", str(file_or_path))
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type '{ext}'. Use: {', '.join(sorted(SUPPORTED))}")
    if ext in {".csv", ".tsv"}:
        sep = "\t" if ext == ".tsv" else None
        try:
            return pd.read_csv(file_or_path, sep=sep, engine="python")
        except UnicodeDecodeError:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            return pd.read_csv(file_or_path, sep=sep, engine="python", encoding="latin-1")
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(file_or_path, sheet_name=sheet_name)
    raw = file_or_path.read() if hasattr(file_or_path, "read") else Path(file_or_path).read_text()
    return pd.json_normalize(json.loads(raw))


def load_api(url: str, headers: dict | None = None, timeout: int = 20) -> pd.DataFrame:
    """Fetch JSON from a REST endpoint and flatten it into a DataFrame."""
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        payload = json.loads(r.read().decode("utf-8"))
    if isinstance(payload, dict):
        lists = [v for v in payload.values() if isinstance(v, list)]
        payload = lists[0] if lists else [payload]
    return pd.json_normalize(payload)


def load_sql(connection_url: str, query: str) -> pd.DataFrame:
    """Run a read-only SELECT against any SQLAlchemy-supported database."""
    ok, reason = validate_sql(query, allowed_tables=None, dialect=None)
    if not ok:
        raise ValueError(f"Query rejected: {reason}")
    from sqlalchemy import create_engine
    engine = create_engine(connection_url)
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


def safe_table_name(name: str) -> str:
    stem = Path(name).stem
    clean = re.sub(r"\W+", "_", stem).strip("_").lower() or "data"
    return clean if not clean[0].isdigit() else f"t_{clean}"
