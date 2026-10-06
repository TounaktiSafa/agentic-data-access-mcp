import os
import threading

import duckdb

DB_PATH = os.getenv("WAREHOUSE_PATH", "data/shop.duckdb")


def connect() -> duckdb.DuckDBPyConnection:
    # read_only: no writes. enable_external_access=False: no file/network reads.
    return duckdb.connect(DB_PATH, read_only=True, config={"enable_external_access": False})


def run_select(sql: str, timeout_s: float = 5.0, max_rows: int = 100):
    con = connect()
    timer = threading.Timer(timeout_s, con.interrupt)  # DuckDB has no native timeout
    timer.start()
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(max_rows)
        return cols, rows
    finally:
        timer.cancel()
        con.close()
