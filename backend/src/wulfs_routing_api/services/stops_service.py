import os
from typing import Tuple
import folium
import logging

import pandas as pd

from wulfs_routing_api.models.stops.stop_model import StopModel

logger = logging.getLogger(__name__)

class StopService():
    def __init__(self, model: StopModel):
        self.model = model

    def persist_stops(self, merged_df, route_id_map):
        stops_to_insert = []

        # Vectorized-ish approach: single pass through the dataframe
        for _, row in merged_df.iterrows():
            driver_idx = int(row["driver_index"])
            route_id = route_id_map.get(driver_idx)

            if not route_id:
                continue  # Skip if no matching route (shouldn’t happen)

            # Safe parsing of numeric fields
            def safe_int(val):
                try:
                    return int(float(val)) if pd.notna(val) else None
                except (ValueError, TypeError):
                    return None

            stops_to_insert.append({
                "route_id": route_id,
                "customer_id": safe_int(row.get("customer_id")),
                "order_id": safe_int(row.get("order_id")),
                "notes": row.get("notes"),
            })

        # Bulk insert all stops at once
        if stops_to_insert:
            self.model.create(stops_to_insert)