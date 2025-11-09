# This code was embedded in the backend but called directly
# Moving here for now

import os
import datetime as dt
from typing import Tuple
import folium
import numpy as np
import pandas as pd
from realtime import Optional
import requests
import constants as const

# Optional clustering dependency
try:
    from sklearn.cluster import KMeans
    HAVE_SK = True
except Exception:
    HAVE_SK = False


def save_routes_map(df: pd.DataFrame, outdir: str, route_date: str, depot_coords: Tuple[float, float], sequences: dict):
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
    print(f"🗺️  Saved routes map to {map_path}")


def samsara_upload_unsequenced(df_driver: pd.DataFrame, token: str, route_name: str,
                               depot_lat: float, depot_lon: float, start_local: dt.datetime,
                               driver_id: Optional[str] = None):
    stops = [{
        "singleUseLocation": {"address":"Depot","latitude":depot_lat,"longitude":depot_lon},
        "scheduledDepartureTime": start_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")
    }]
    arrival_time = start_local
    for i, (_, r) in enumerate(df_driver.iterrows()):
        # Increment start time by 15 mins for each stop
        arrival_time = start_local + dt.timedelta(minutes=15 * (i + 1))
        stops.append({
            "singleUseLocation": {
                "address": f'{r["address"]}, {r["city"]}, {r["state"]} {r["zip"]}',
                "latitude": float(r["lat"]),
                "longitude": float(r["lon"])
            },
            "scheduledArrivalTime": arrival_time.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "notes": str(r.get("notes",""))[:2000]
        })

    # Add final stop to return to depot
    final_arrival_time = arrival_time + dt.timedelta(minutes=15)
    stops.append({
        "singleUseLocation": {"address": "Depot", "latitude": depot_lat, "longitude": depot_lon},
        "scheduledArrivalTime": final_arrival_time.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    })
    payload = {
        "name": route_name,
        "stops": stops,
        "settings": {
            "routeStartingCondition":"departFirstStop",
            "routeCompletionCondition":"arriveLastStop"
        }
    }
    if driver_id:
        payload["driverId"] = str(driver_id)
    headers = {"Authorization": f'Bearer {os.getenv("SAMSARA_API_TOKEN","")}', "Content-Type":"application/json"}
    r = requests.post(const.SAMSARA_ROUTES_URL, headers=headers, json=payload, timeout=30)
    if r.status_code not in (200,201):
        raise RuntimeError(f"Samsara create route error {r.status_code}: {r.text[:300]}")
    return r.json()


def export_assignments(merged: pd.DataFrame, labels: np.ndarray, outdir: str, route_date: str) -> pd.DataFrame:
    os.makedirs(outdir, exist_ok=True)
    out = merged.copy()
    out["driver_index"] = labels
    bundles = []
    for d in sorted(np.unique(labels)):
        df_d = out[out["driver_index"]==d].copy()
        cols = ["driver_index","order_id","customer_name","address","city","state","zip","lat","lon","notes"]
        for c in cols:
            if c not in df_d.columns:
                df_d[c] = "" if c not in ("lat","lon") else np.nan
        df_d = df_d[cols]
        df_d.to_csv(os.path.join(outdir, f"driver{d+1}_{route_date}.csv"), index=False)
        bundles.append(df_d)
    all_df = pd.concat(bundles, ignore_index=True)
    all_df.to_csv(os.path.join(outdir, f"routes_assigned_{route_date}.csv"), index=False)
    return all_df

