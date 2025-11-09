import os
import re
import unicodedata
import pandas as pd
from realtime import List, Optional
# -------------------- Normalization --------------------

_norm_space = re.compile(r"\s+")
_norm_keep = re.compile(r"[^a-z0-9 ]")  # keep alphanumerics + spaces

def norm_name(s: str) -> str:
    """Normalize customer names: unicode→ascii, lowercase, strip punctuation, collapse spaces."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    s = s.strip().lower()
    s = _norm_keep.sub("", s)
    s = _norm_space.sub(" ", s).strip()
    return s

def _find(master_cols: List[str], candidates: List[str]) -> Optional[str]:
    low = {c.lower().strip(): c for c in master_cols}
    for cand in candidates:
        if cand in low:
            return low[cand]
    return None

# -------------------- Utils & IO --------------------

def read_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)

# -------------------- Loaders --------------------

def load_master(master_path: str) -> pd.DataFrame:
    df = read_table(master_path).copy()
    cols = df.columns.tolist()

    name_c = _find(cols, ["customer name", "customer_name", "name"])
    addr_c = _find(cols, ["street address", "address", "street"])
    city_c = _find(cols, ["city"])
    state_c = _find(cols, ["state"])
    zip_c = _find(cols, ["zip", "zipcode", "postal code", "postal"])
    lat_c = _find(cols, ["latitude", "lat"])
    lon_c = _find(cols, ["longitude", "lon", "lng"])

    missing = [lab for lab, c in [
        ("Customer Name", name_c), ("Street Address", addr_c), ("City", city_c),
        ("State", state_c), ("ZIP", zip_c), ("Latitude", lat_c), ("Longitude", lon_c)
    ] if c is None]
    if missing:
        raise ValueError(f"Master missing required columns (case-insensitive): {missing}")

    df = df.rename(columns={
        name_c: "customer_name",
        addr_c: "address",
        city_c: "city",
        state_c: "state",
        zip_c: "zip",
        lat_c: "lat",
        lon_c: "lon",
    })

    # normalized name key for joining
    df["name_key"] = df["customer_name"].apply(norm_name)
    return df

# TODO Check for usage (Does not appear to be used)
def load_orders(orders_path: str) -> pd.DataFrame:
    df = read_table(orders_path).copy()
    cols = {c.lower().strip(): c for c in df.columns}

    # Minimal: Customer Name
    if "customer name" not in cols and "customer_name" not in cols and "name" not in cols:
        raise ValueError("Orders must include a 'Customer Name' column (any case).")

    name_c = cols.get("customer name") or cols.get("customer_name") or cols.get("name")
    df = df.rename(columns={name_c: "customer_name"})
    if "order id" in cols:
        df = df.rename(columns={cols["order id"]: "order_id"})
    if "notes" in cols:
        df = df.rename(columns={cols["notes"]: "notes"})
    if "order_id" not in df.columns:
        df["order_id"] = ""
    if "notes" not in df.columns:
        df["notes"] = ""

    df["name_key"] = df["customer_name"].apply(norm_name)
    return df