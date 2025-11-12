import re
from shapely import wkb
import pandas as pd
from wulfs_routing_api.models.supabase_db import supabase
from wulfs_routing_api.models.customers.customer_model import CustomerModel

class SupabaseCustomer(CustomerModel):
    def get_all_customers(self) -> pd.DataFrame:
        response = supabase.table('customers').select("id, name_key, name, address, city, state, zip, lat, lon").execute()
        customer_df = pd.DataFrame(response.data)
        customer_df = customer_df.rename(columns={"id": "customer_id", "name": "customer_name"})
        return customer_df
    