import sqlite3
from contextlib import closing

from fastapi import FastAPI, HTTPException

import pipeline

DB_PATH = "data/api.db"

app = FastAPI(title="Vellamo Sales Pipeline")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(rows: list[dict]):
    if not rows:
        raise HTTPException(status_code=422, detail="Send a non-empty list of records")
    with closing(sqlite3.connect(DB_PATH)) as con:
        pipeline.init_db(con)
        return pipeline.process_batch(rows, con)


@app.get("/summary")
def summary():
    with closing(sqlite3.connect(DB_PATH)) as con:
        pipeline.init_db(con)
        orders, revenue = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_sales_kes), 0) FROM sales_clean"
        ).fetchone()
        by_payment = con.execute(
            "SELECT payment_method, COUNT(*), SUM(total_sales_kes) "
            "FROM sales_clean GROUP BY payment_method ORDER BY 3 DESC"
        ).fetchall()
    return {
        "orders": orders,
        "revenue_kes": revenue,
        "by_payment": [{"method": m, "orders": n, "revenue_kes": r} for m, n, r in by_payment],
    }