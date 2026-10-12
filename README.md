# Vellamo Sales Pipeline

An end-to-end data pipeline that takes raw JSON sales records, validates and cleans them with Pandas, and stores them in a SQL database, exposed through a FastAPI service.

Built for the MCD challenge (Day 27, D Protocol) using Vellamo Fashion FY2025 sales data (3,758 transactions, Jan-Dec 2025, Kenya).

## How it works

```
raw JSON  ->  POST /ingest (FastAPI)  ->  Pandas: rename, type-convert, validate  ->  SQLite
                                                   |-> sales_clean     (valid rows)
                                                   |-> sales_rejected  (bad rows + reason)
```

## Validation rules
Each rejected row gets exactly one reason (first failing rule wins):
`missing_transaction_id`, `duplicate_transaction_id`, `invalid_date`, `invalid_quantity`, `missing_amount`, `negative_price_or_cost`, `total_sales_mismatch`, `profit_mismatch`.

Nothing is silently dropped: stored + already_loaded + rejected always equals received.

## Design decisions
- **Quarantine, don't delete:** rejected rows are kept with their raw JSON and reason.
- **Idempotent loads:** sending the same file twice stores nothing new.
- **Two guards:** Pandas validation first, then database constraints (PRIMARY KEY, CHECK) as a last line of defense.

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/ingest` | Send a JSON list of raw records, returns a batch summary |
| GET | `/summary` | Orders, total revenue, and revenue by payment method |
| GET | `/health` | Service check |

## Run it
```bash
pip install fastapi uvicorn pandas pytest httpx
uvicorn main:app --reload      # API docs at http://127.0.0.1:8000/docs
python -m pytest -v            # run the tests
```

## Files
- `pipeline.py` - schema, validation, storage, `process_batch`
- `main.py` - FastAPI app
- `test_api.py` - automated tests
- `test_output.txt` - verification test output
- `1_money96.ipynb` - exploration and step-by-step build

## Stack
Python, FastAPI, Pandas, SQLite, pytest"# End-to-end-Engine" 
