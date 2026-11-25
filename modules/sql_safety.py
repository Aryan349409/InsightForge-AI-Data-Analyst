"""Static validation of LLM-generated SQL.

Rule of thumb: never trust generated SQL. We parse it with sqlglot and accept
only a single read-only query that touches only whitelisted tables and no
file-reading functions. Execution additionally disables DuckDB external access.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

_FORBIDDEN_NODES = tuple(
    getattr(exp, n) for n in (
        "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command",
        "Copy", "Merge", "Set", "Use", "Pragma", "Attach", "Detach", "TruncateTable",
        "Transaction", "Commit", "Rollback",
    ) if hasattr(exp, n)
)
_QUERY = getattr(exp, "Query", exp.Select)
_BAD_FUNC_PREFIXES = ("read_", "glob", "write_", "copy_", "pg_", "sqlite_", "duckdb_", "load_")


def validate_sql(sql: str, allowed_tables: set[str] | None = None,
                 dialect: str | None = "duckdb") -> tuple[bool, str]:
    """Return (is_safe, reason)."""
    if not sql or not sql.strip():
        return False, "Empty SQL."
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as e:
        return False, f"SQL could not be parsed: {str(e)[:150]}"
    if len(statements) != 1:
        return False, "Exactly one statement is allowed."
    tree = statements[0]
    if not isinstance(tree, _QUERY):
        return False, "Only SELECT queries are allowed."
    for node in tree.walk():
        node = node[0] if isinstance(node, tuple) else node
        if isinstance(node, _FORBIDDEN_NODES):
            return False, f"Forbidden operation: {type(node).__name__}."
        if isinstance(node, (exp.Anonymous, exp.Func)):
            name = (node.name or type(node).__name__).lower()
            if name.startswith(_BAD_FUNC_PREFIXES):
                return False, f"Forbidden function: {name}."
    if allowed_tables is not None:
        allowed = {t.lower() for t in allowed_tables}
        ctes = {c.alias.lower() for c in tree.find_all(exp.CTE) if c.alias}
        for t in tree.find_all(exp.Table):
            if not isinstance(t.this, exp.Identifier):
                return False, "Table functions are not allowed."
            if t.name.lower() not in allowed | ctes:
                return False, f"Table '{t.name}' is not available."
    return True, "ok"


def enforce_limit(sql: str, limit: int = 1000) -> str:
    """Wrap the query so a runaway result can't flood the UI."""
    return f"SELECT * FROM ({sql.strip().rstrip(';')}) AS _q LIMIT {int(limit)}"
