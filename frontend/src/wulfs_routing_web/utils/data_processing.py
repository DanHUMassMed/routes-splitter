import re
import pandas as pd
from typing import Any, Tuple
from shapely import wkb
import os
import numpy as np

# --- Data Processing Helper ---
def parse_point(point_data):
    """Parse a PostGIS WKB (hex), WKT, or GeoJSON-style point.

    Args:
        point_data (str | dict): Geometry as hex string, WKT, or dict with 'coordinates'.
    Returns:
        tuple[float | None, float | None]: (lon, lat)
    """
    # Case 1: GeoJSON-style dict
    if isinstance(point_data, dict) and "coordinates" in point_data:
        coords = point_data["coordinates"]
        if len(coords) == 2:
            return float(coords[0]), float(coords[1])

    # Case 2: WKT string
    if isinstance(point_data, str) and point_data.startswith("POINT("):
        import re
        match = re.match(r"POINT\(([-+]?\d*\.?\d+) ([-+]?\d*\.?\d+)\)", point_data)
        if match:
            lon, lat = float(match.group(1)), float(match.group(2))
            return lon, lat

    # Case 3: WKB hex string
    if isinstance(point_data, str):
        try:
            geom = wkb.loads(bytes.fromhex(point_data))
            return float(geom.x), float(geom.y)
        except Exception:
            pass

    # Fallback
    return None, None

def process_routes_from_api(route_stops_data):
    """Transforms the API response from /routes/{route_id}/stops into a DataFrame."""
    records = []
    for stop in route_stops_data:
        customer_data = stop.get('customers', {})
        lon, lat = parse_point(customer_data.get('location'))
        records.append({
            "vehicle_index": stop['route_id'], # Using route_id to group vehicles for now
            "order_id": stop.get('order_id'),
            "customer_name": customer_data.get('name'),
            "address": customer_data.get('address'),
            "city": customer_data.get('city'),
            "state": customer_data.get('state'),
            "zip": customer_data.get('zip'),
            "lat": lat,
            "lon": lon,
            "sequence":stop.get('stop_sequence'),
            "notes": stop.get('notes'),
        })
    return pd.DataFrame(records)

def export_assignments(routes_df: pd.DataFrame, outdir: str, route_date: str) -> pd.DataFrame:
    """Exports the vehicle assignments to CSV files."""
    os.makedirs(outdir, exist_ok=True)
    
    if "vehicle_index" not in routes_df.columns:
        return pd.DataFrame()

    unique_vehicles = sorted(routes_df["vehicle_index"].unique())
    
    bundles = []
    for d in unique_vehicles:
        df_d = routes_df[routes_df["vehicle_index"] == d].copy()
        cols = ["vehicle_index", "order_id", "customer_name", "address", "city", "state", "zip", "lat", "lon", "notes"]
        
        # Ensure all required columns exist
        for c in cols:
            if c not in df_d.columns:
                df_d[c] = "" if c not in ("lat", "lon") else np.nan
        
        df_d = df_d[cols]
        df_d.to_csv(os.path.join(outdir, f"vehicle{d+1}_{route_date}.csv"), index=False)
        bundles.append(df_d)
        
    if not bundles:
        return pd.DataFrame()

    all_df = pd.concat(bundles, ignore_index=True)
    all_df.to_csv(os.path.join(outdir, f"routes_assigned_{route_date}.csv"), index=False)
    return all_df