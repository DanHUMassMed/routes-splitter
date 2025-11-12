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

    def persist_stops(self, stops_df, route_id_map):
        stops_to_insert = []
        stop_sequences = {}
        for _, row in stops_df.iterrows():
            vehicle_idx = int(row["vehicle_index"])
            route_id = route_id_map.get(vehicle_idx)
            stop_sequences[vehicle_idx] = stop_sequences.get(vehicle_idx, 0) + 1

            if not route_id:
                continue  # Skip if no matching route (shouldn’t happen)

            stops_to_insert.append({
                "route_id": int(route_id),
                "customer_id": int(row.get("customer_id")),
                "sequence": int(stop_sequences[vehicle_idx]),
                "notes": row.get("notes",""),
            })

        # Bulk insert all stops at once
        if stops_to_insert:
            self.model.create(stops_to_insert)

    def get_stops_for_route(self, route_id):
            return self.model.get_stops_for_route(route_id)