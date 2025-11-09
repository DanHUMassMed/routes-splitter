
import re
import unicodedata
import pandas as pd

from wulfs_routing_api.utils.data_io_utils import read_table
import re
import pandas as pd
from wulfs_routing_api.models.orders.order_model import OrderModel

class OrderService():
    def __init__(self, model: OrderModel):
        self.model = model
        self.norm_space = re.compile(r"\s+")
        self.norm_keep = re.compile(r"[^a-z0-9 ]")  # keep alphanumerics + spaces

    def _norm_name(self, s: str) -> str:
        """Normalize customer names: unicode→ascii, lowercase, strip punctuation, collapse spaces."""
        if s is None:
            return ""
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
        s = s.strip().lower()
        s = self.norm_keep.sub("", s)
        s = self.norm_space.sub(" ", s).strip()
        return s

    def load_orders(self, orders_path: str) -> pd.DataFrame:
        
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

        df["name_key"] = df["customer_name"].apply(self._norm_name)
        return df

    def customer_details_for_orders(self, orders_df, master_df):
        merged_df = orders_df.merge(
            master_df, # Merge with the full dataframe from DB
            on="name_key",
            how="left",
            suffixes=('_order', '')
        )
        #TODO this smells bad
        missing_customers_df = merged_df[merged_df["lat"].isna() | merged_df["lon"].isna()]
        merged_df = merged_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
        return merged_df, missing_customers_df
