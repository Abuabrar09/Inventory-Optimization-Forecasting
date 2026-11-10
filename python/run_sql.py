import sys
import duckdb

# Usage: python python/run_sql.py sql/<file>.sql
con = duckdb.connect("inventory.duckdb")
sql_text = open(sys.argv[1]).read()

lines = [l for l in sql_text.splitlines() if not l.strip().startswith("--")]
statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
print(f"Running {len(statements)} statements from {sys.argv[1]}\n")

for stmt in statements:
    first_word = stmt.split()[0].upper()
    if first_word in ("SELECT", "WITH"):
        print(con.sql(stmt).df().to_string(index=False))   # show query results
        print("-" * 60)
    else:
        con.execute(stmt)                                   # CREATE / INSERT: just run it
        print("OK:", " ".join(stmt.split()[:5]), "...")
        