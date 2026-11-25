"""Natural-language -> SQL engine with validation, safe execution and self-repair."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import duckdb
import pandas as pd

from modules.sql_safety import enforce_limit, validate_sql

SYSTEM_PROMPT = """You are a careful senior data analyst who writes DuckDB SQL.
Rules:
- Output ONE read-only SELECT query inside a ```sql code block. No explanations.
- Use ONLY the table and columns listed in the schema. Quote identifiers if needed.
- Never use INSERT/UPDATE/DELETE/DROP/CREATE or file functions.
- For "top N" questions use ORDER BY ... DESC LIMIT N.
- Round monetary or ratio results to 2 decimals.
- If the question cannot be answered from the schema, output: SELECT 'UNANSWERABLE' AS answer;"""


@dataclass
class QueryResult:
    question: str
    sql: str = ""
    df: pd.DataFrame | None = None
    error: str | None = None
    attempts: int = 0
    latency: float = 0.0
    history: list[str] = field(default_factory=list)  # SQL attempts incl. failed ones

    @property
    def ok(self) -> bool:
        return self.error is None and self.df is not None


def schema_context(df: pd.DataFrame, table: str, n_examples: int = 3) -> str:
    lines = [f"Table: {table}  ({len(df)} rows)", "Columns:"]
    for c in df.columns:
        s = df[c]
        ex = s.dropna().astype(str).unique()[:n_examples]
        extra = ""
        if pd.api.types.is_numeric_dtype(s) and s.notna().any():
            extra = f" range[{s.min():.4g}, {s.max():.4g}]"
        elif pd.api.types.is_datetime64_any_dtype(s) and s.notna().any():
            extra = f" range[{s.min().date()}, {s.max().date()}]"
        lines.append(f"  - {c} ({s.dtype}){extra} e.g. {', '.join(map(str, ex))}")
    return "\n".join(lines)


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    return sql.rstrip(";").strip()


def execute_sql(df: pd.DataFrame, table: str, sql: str, limit: int = 1000) -> pd.DataFrame:
    """Run validated SQL in an isolated in-memory DuckDB with external access off."""
    con = duckdb.connect(":memory:")
    try:
        con.register(table, df)
        try:
            con.execute("SET enable_external_access=false")
        except duckdb.Error:
            pass
        return con.execute(enforce_limit(sql, limit)).df()
    finally:
        con.close()


def ask(llm, question: str, df: pd.DataFrame, table: str = "data",
        chat_history: list[tuple[str, str]] | None = None, max_retries: int = 2) -> QueryResult:
    """Translate a question to SQL, validate, execute, and self-repair on failure."""
    res = QueryResult(question=question)
    start = time.perf_counter()
    context = schema_context(df, table)
    prior = ""
    if chat_history:
        prior = "Earlier questions and the SQL used:\n" + "\n".join(
            f"Q: {q}\nSQL: {s}" for q, s in chat_history[-3:]) + "\n\n"
    prompt = f"{context}\n\n{prior}Question: {question}"
    error_note = ""
    for attempt in range(max_retries + 1):
        res.attempts = attempt + 1
        user = prompt + (f"\n\nYour previous SQL failed.\n{error_note}\nFix it." if error_note else "")
        try:
            raw = llm.complete(SYSTEM_PROMPT, user, max_tokens=700)
        except Exception as e:  # network / auth problems - no point retrying
            res.error = f"LLM error: {e}"
            break
        sql = extract_sql(raw)
        res.sql = sql
        res.history.append(sql)
        ok, reason = validate_sql(sql, allowed_tables={table})
        if not ok:
            error_note = f"SQL:\n{sql}\nValidation error: {reason}"
            res.error = f"Blocked: {reason}"
            continue
        try:
            res.df = execute_sql(df, table, sql)
            res.error = None
            break
        except Exception as e:
            error_note = f"SQL:\n{sql}\nDuckDB error: {e}"
            res.error = f"Execution error: {e}"
    res.latency = time.perf_counter() - start
    return res
