import os
import folium
import pandas as pd
from typing import Tuple

def generate_route_map(df: pd.DataFrame, outdir: str, route_date: str, depot_coords: Tuple[float, float], sequences: dict):
    """
    Saves an HTML map of the routes. 
    Note: The stops displayed are unsequenced; this map is for visualizing vehicle assignments, not optimized delivery order.
    Returns the path to the saved map file.
    """
    m = folium.Map(location=[depot_coords[1], depot_coords[0]], zoom_start=10)
    
    # Add depot marker
    folium.Marker(
        location=[depot_coords[1], depot_coords[0]],
        popup="Depot",
        icon=folium.Icon(color="red", icon="info-sign"),
    ).add_to(m)

    colors = ["blue", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "white", "pink", "lightblue", "lightgreen", "gray", "black", "lightgray"]

    # If sequences are not provided, we can just show the stops for each vehicle
    if not sequences:
        for vehicle_index in df["vehicle_index"].unique():
            vehicle_df = df[df["vehicle_index"] == vehicle_index]
            color = colors[vehicle_index % len(colors)]
            for _, row in vehicle_df.iterrows():
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    popup=f"<b>{row['customer_name']}</b><br>Vehicle: {vehicle_index + 1}",
                    icon=folium.Icon(color=color, icon="truck", prefix="fa"),
                ).add_to(m)
    else:
        for vehicle_index, seq in sequences.items():
            color = colors[vehicle_index % len(colors)]
            route_points = [(depot_coords[1], depot_coords[0])]
            for original_df_index in seq:
                if original_df_index != 0: # 0 is the depot
                    row = df.loc[original_df_index]
                    route_points.append((row["lat"], row["lon"])) 
            route_points.append((depot_coords[1], depot_coords[0]))

            folium.PolyLine(route_points, color=color, weight=2.5, opacity=1).add_to(m)

            for original_df_index in seq:
                if original_df_index != 0: # 0 is the depot
                    row = df.loc[original_df_index]
                    folium.Marker(
                        location=[row["lat"], row["lon"]],
                        popup=f"<b>{row['customer_name']}</b>",
                        icon=folium.Icon(color=color, icon="truck", prefix="fa"),
                    ).add_to(m)
                    
    os.makedirs(outdir, exist_ok=True)
    map_path = os.path.join(outdir, f"routes_map_{route_date}.html")
    m.save(map_path)
    print(f"🗺️  Saved routes map to {map_path}")
    return map_path
