import os
from typing import Tuple
import folium
import logging

import pandas as pd

from wulfs_routing_api.models.routes.route_model import RouteModel

logger = logging.getLogger(__name__)

class RouteService():
    def __init__(self, model: RouteModel):
        self.model = model

    def persist_routes(self,merged_df, route_date_str):
        routes_to_insert = []
        driver_indices = sorted(merged_df["driver_index"].unique())

        for driver_idx in driver_indices:
            routes_to_insert.append({
                "route_date": route_date_str,
                "driver_index": int(driver_idx),
                "route_name": f"Deliveries {route_date_str} - Driver {driver_idx + 1}",
            })

        response_data  = self.model.create(routes_to_insert)

        # Build a mapping driver_index -> route_id
        created_map = {
            route["driver_index"]: route["id"]
            for route in response_data
        }

        return created_map
    
    def save_routes_map(self,df: pd.DataFrame, outdir: str, route_date: str, depot_coords: Tuple[float, float], sequences: dict):
        """Saves an HTML map of the routes. Note: The stops displayed are unsequenced; this map is for visualizing driver assignments, not optimized delivery order."""
        m = folium.Map(location=[depot_coords[1], depot_coords[0]], zoom_start=10)
        
        # Add depot marker
        folium.Marker(
            location=[depot_coords[1], depot_coords[0]],
            popup="Depot",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

        colors = ["blue", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "white", "pink", "lightblue", "lightgreen", "gray", "black", "lightgray"]

        for driver_index, seq in sequences.items():
            color = colors[driver_index % len(colors)]
            
            # Construct route points based on the optimized sequence
            route_points = [(depot_coords[1], depot_coords[0])]
            for original_df_index in seq:
                if original_df_index != 0: # 0 is the depot, already added
                    row = df.loc[original_df_index]
                    route_points.append((row["lat"], row["lon"])) 
            # Add depot as the last stop for visualization
            route_points.append((depot_coords[1], depot_coords[0]))

            folium.PolyLine(route_points, color=color, weight=2.5, opacity=1).add_to(m)

            # Add markers for each stop in the optimized sequence
            for original_df_index in seq:
                if original_df_index != 0: # 0 is the depot
                    row = df.loc[original_df_index]
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        popup=f"<b>{row['customer_name']}</b>",
                        icon=folium.Icon(color=color, icon="truck", prefix="fa"),
                    ).add_to(m)
                        
        map_path = os.path.join(outdir, f"routes_map_{route_date}.html")
        m.save(map_path)
        logger.debug(f"🗺️  Saved routes map to {map_path}")
