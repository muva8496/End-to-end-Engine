import sqlite3
import pandas as pd

COLUMN_MAP = {
    "Transaction ID": "transaction_id", "Date": "sale_date", "City": "city",
    "Branch": "branch", "Category": "category", "Product": "product",
    "Quantity": "quantity", "Unit Price (KES)": "unit_price_kes",
    "Unit Cost (KES)": "unit_cost_kes", "Total Sales (KES)": "total_sales_kes",
    "Total Cost (KES)": "total_cost_kes", "Profit (KES)": "profit_kes",
    "Sales Channel": "sales_channel", "Payment Method": "payment_method",
    "Customer Gender": "customer_gender", "Customer Age Group": "customer_age_group",
    "Salesperson": "salesperson",
}
NUMERIC = ["transaction_id", "quantity", "unit_price_kes", "unit_cost_kes",
           "total_sales_kes", "total_cost_kes", "profit_kes"]
AMOUNTS = ["unit_price_kes", "unit_cost_kes", "total_sales_kes", "total_cost_kes", "profit_kes"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_clean (
    transaction_id INTEGER PRIMARY KEY, sale_date TEXT NOT NULL,
    city TEXT, branch TEXT, category TEXT, product TEXT,
    quantity INTEGER NOT NULL CHECK (quantity >= 1),
    unit_price_kes INTEGER NOT NULL CHECK (unit_price_kes >= 0),
    unit_cost_kes INTEGER NOT NULL CHECK (unit_cost_kes >= 0),
    total_sales_kes INTEGER NOT NULL, total_cost_kes INTEGER NOT NULL,
    profit_kes INTEGER NOT NULL, sales_channel TEXT, payment_method TEXT,
    customer_gender TEXT, customer_age_group TEXT, salesperson TEXT
);
CREATE TABLE IF NOT EXISTS sales_rejected (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reject_reason TEXT NOT NULL, raw_json TEXT NOT NULL
);
"""

def init_db(con):
    con.executescript(SCHEMA)

def validate(df):
    rules = [
        ("missing_transaction_id", df["transaction_id"].isna()),
        ("duplicate_transaction_id", df["transaction_id"].duplicated(keep="first")),
        ("invalid_date", df["sale_date"].isna()),
        ("invalid_quantity", df["quantity"].isna() | (df["quantity"] < 1)),
        ("missing_amount", df[AMOUNTS].isna().any(axis=1)),
        ("negative_price_or_cost", (df["unit_price_kes"] < 0) | (df["unit_cost_kes"] < 0)),
        ("total_sales_mismatch", df["quantity"] * df["unit_price_kes"] != df["total_sales_kes"]),
        ("profit_mismatch", df["total_sales_kes"] - df["total_cost_kes"] != df["profit_kes"]),
    ]
    reason = pd.Series("", index=df.index)
    for name, failed in rules:
        reason = reason.mask((reason == "") & failed, name)
    clean = df[reason == ""]
    rejects = df[reason != ""].assign(reject_reason=reason[reason != ""])
    return clean, rejects

def store(con, clean, rejects):
    if len(clean):
        out = clean.copy()
        for c in NUMERIC:
            out[c] = out[c].astype(int)
        out["sale_date"] = out["sale_date"].dt.strftime("%Y-%m-%d")
        out.to_sql("sales_clean", con, if_exists="append", index=False)
    if len(rejects):
        rej = pd.DataFrame({
            "reject_reason": rejects["reject_reason"].values,
            "raw_json": [r.to_json(date_format="iso")
                         for _, r in rejects.drop(columns="reject_reason").iterrows()],
        })
        rej.to_sql("sales_rejected", con, if_exists="append", index=False)
    con.commit()

def process_batch(raw, con):
    df = pd.DataFrame(raw).rename(columns=COLUMN_MAP)
    for col in COLUMN_MAP.values():
        if col not in df.columns:
            df[col] = None
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["sale_date"] = pd.to_datetime(df["sale_date"], format="%Y-%m-%d", errors="coerce")

    clean, rejects = validate(df)
    existing = {r[0] for r in con.execute("SELECT transaction_id FROM sales_clean")}
    already = clean["transaction_id"].astype(int).isin(existing)
    new = clean[~already]
    store(con, new, rejects)
    return {
        "received": len(df),
        "stored": len(new),
        "already_loaded": int(already.sum()),
        "rejected": len(rejects),
        "reject_reasons": rejects["reject_reason"].value_counts().to_dict(),
    }