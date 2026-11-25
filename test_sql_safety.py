import pytest
from modules.sql_safety import validate_sql

T = {"data"}

@pytest.mark.parametrize("sql", [
    "SELECT * FROM data",
    "SELECT product, SUM(revenue) FROM data GROUP BY 1 ORDER BY 2 DESC LIMIT 5",
    "WITH t AS (SELECT * FROM data) SELECT COUNT(*) FROM t",
    "SELECT a.x FROM data a JOIN data b ON a.x = b.x",
    "SELECT * FROM data UNION ALL SELECT * FROM data",
])
def test_safe_queries_pass(sql):
    assert validate_sql(sql, T)[0]

@pytest.mark.parametrize("sql", [
    "DROP TABLE data",
    "DELETE FROM data",
    "UPDATE data SET x = 1",
    "INSERT INTO data VALUES (1)",
    "CREATE TABLE t AS SELECT * FROM data",
    "SELECT * FROM data; DROP TABLE data",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM other_table",
    "COPY data TO '/tmp/x.csv'",
    "ATTACH 'x.db'",
    "PRAGMA database_list",
    "",
])
def test_dangerous_queries_blocked(sql):
    assert not validate_sql(sql, T)[0]

def test_unparseable_sql_rejected():
    assert not validate_sql("SELEC FROM WHERE", T)[0]
