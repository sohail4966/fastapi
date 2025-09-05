# run_migrations.py
import hashlib, os, re, socket, sys, time
from pathlib import Path
from filelock import FileLock
import clickhouse_connect

from core.config import settings

MIG_DIR = Path("migrations")

SQL_COMMENT = re.compile(r"--.*?$|/\*.*?\*/", re.S | re.M)

def normalize(sql: str) -> str:
    s = SQL_COMMENT.sub("", sql).strip()
    return s[:-1].strip() if s.endswith(";") else s

def single_stmt(sql: str) -> bool:
    body = sql.strip()
    if body.endswith(";"):
        body = body[:-1]
    return ";" not in body

LEDGER_DDL = """
CREATE TABLE IF NOT EXISTS migration_ledger (
  id String,
  description String,
  checksum String,
  applied_at DateTime64(3) DEFAULT now64(3),
  applied_by String DEFAULT currentUser(),
  host String,
  phase Enum8('committing'=1,'committed'=2,'aborted'=3),
  duration_ms UInt64,
  error String
) ENGINE=MergeTree ORDER BY (id)
"""

def migration_sort_key(path: Path) -> tuple[int, str]:
    """Extract numeric prefix for proper ordering (supports 1_, 0001_ etc)."""
    name = path.stem
    parts = name.split("_", 1)
    try:
        num = int(parts[0])
    except Exception:
        num = 999999  # fallback if no numeric prefix
    return (num, name)

def log_phase(client, mid, desc, chk, host, phase, dur=0, err=""):
    client.insert(
        "migration_ledger",
        [(mid, desc, chk, host, phase, int(dur), err)],
        column_names=["id","description","checksum","host","phase","duration_ms","error"]
    )

def main():
    # build client from your settings (core.config.settings)
    client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        database=settings.CLICKHOUSE_DATABASE,
        username=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD
    )

    # ensure ledger exists
    client.command(LEDGER_DDL)

    # find already committed migrations
    done = {r[0] for r in client.query(
        "SELECT id FROM migration_ledger WHERE phase='committed'"
    ).result_rows}

    host = socket.gethostname()
    lock = FileLock("/tmp/py_migrator.lock")

    if not MIG_DIR.exists() or not MIG_DIR.is_dir():
        print(f"[ERROR] migrations dir not found: {MIG_DIR.resolve()}", file=sys.stderr)
        sys.exit(1)

    with lock:
        files = sorted(MIG_DIR.glob("*.sql"), key=migration_sort_key)
        for sql_path in files:
            # skip verify files (we treat them separately)
            if sql_path.name.endswith(".verify.sql"):
                continue

            mid = sql_path.stem
            if mid in done:
                # already applied
                continue

            raw = sql_path.read_text(encoding="utf-8")
            lines = raw.splitlines()
            desc = ""
            if lines and lines[0].strip().startswith("--"):
                desc = lines[0].lstrip("- ").strip()

            stmt = normalize(raw)
            if not single_stmt(stmt):
                print(f"[ERROR] Multiple statements detected in {sql_path.name} — one statement per migration required.", file=sys.stderr)
                sys.exit(2)

            chk = hashlib.sha256(stmt.encode()).hexdigest()
            start = time.time()

            try:
                # mark committing
                log_phase(client, mid, desc, chk, host, "committing", 0, "")

                # execute the atomic DDL
                client.command(stmt)

                # optional verify
                vpath = sql_path.with_suffix(".verify.sql")
                if vpath.exists():
                    vsql = normalize(vpath.read_text(encoding="utf-8"))
                    # you can optionally check results here; if it raises, we treat as failure
                    client.query(vsql)

                dur = int((time.time() - start) * 1000)
                # mark committed (FIXED)
                log_phase(client, mid, desc, chk, host, "committed", dur, "")
                print(f"[OK] Applied {sql_path.name} (took {dur} ms)")
            except Exception as ex:
                dur = int((time.time() - start) * 1000)
                log_phase(client, mid, desc, chk, host, "aborted", dur, str(ex))
                print(f"[ERROR] Migration {mid} failed after {dur} ms: {ex}", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()
