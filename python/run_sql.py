import sys
import duckdb

# Usage: python python/run_sql.py sql/<file>.sql
con = duckdb.connect("inventory.duckdb")
sql_text = open(sys.argv[1]).read()

lines = [l for l in sql_text.splitlines() if not l.strip().startswith("--")]
for stmt in "\n".join(lines).split(";"):
    if stmt.strip():
        result = con.sql(stmt)
        if result is not None:
            print(result.df().to_string(index=False))
            print("-" * 60)