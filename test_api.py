import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    return TestClient(main.app)


def good(i=1, **over):
    row = {
        "Transaction ID": 100000 + i, "Date": "2025-01-01", "City": "Nairobi",
        "Branch": "Vellamo Karen", "Category": "Shoes", "Product": "Heeled Sandals",
        "Quantity": 1, "Unit Price (KES)": 3400, "Unit Cost (KES)": 1970,
        "Total Sales (KES)": 3400, "Total Cost (KES)": 1970, "Profit (KES)": 1430,
        "Sales Channel": "In-Store", "Payment Method": "M-Pesa",
        "Customer Gender": "Female", "Customer Age Group": "25-34",
        "Salesperson": "Kipchoge N.",
    }
    row.update(over)
    return row


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_good_rows_are_stored(client):
    r = client.post("/ingest", json=[good(1), good(2)])
    assert r.status_code == 200
    assert r.json()["stored"] == 2 and r.json()["rejected"] == 0


def test_same_batch_twice_creates_no_duplicates(client):
    batch = [good(1), good(2)]
    client.post("/ingest", json=batch)
    second = client.post("/ingest", json=batch).json()
    assert second["stored"] == 0 and second["already_loaded"] == 2


def test_bad_rows_are_quarantined_with_reasons(client):
    batch = [good(1), good(2, **{"Quantity": 0}), good(3, **{"Profit (KES)": 1})]
    r = client.post("/ingest", json=batch).json()
    assert r["stored"] == 1 and r["rejected"] == 2
    assert r["reject_reasons"] == {"invalid_quantity": 1, "profit_mismatch": 1}


def test_nothing_is_lost(client):
    batch = [good(1), good(2, **{"Quantity": 0}), good(1)]
    r = client.post("/ingest", json=batch).json()
    assert r["stored"] + r["already_loaded"] + r["rejected"] == r["received"]


def test_empty_list_is_rejected_with_422(client):
    assert client.post("/ingest", json=[]).status_code == 422


def test_summary_matches_ingested_data(client):
    client.post("/ingest", json=[good(1), good(2)])
    s = client.get("/summary").json()
    assert s["orders"] == 2 and s["revenue_kes"] == 6800