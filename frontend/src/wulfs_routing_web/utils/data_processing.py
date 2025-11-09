import re
import pandas as pd
from typing import Any, Tuple
from shapely import wkb

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
    """Transforms the API response from /routes/{route_id} into a DataFrame."""
    records = []
    for stop in route_stops_data:
        customer_data = stop.get('customers', {})
        lon, lat = parse_point(customer_data.get('location'))
        records.append({
            "driver_index": stop['route_id'], # Using route_id to group drivers for now
            "order_id": stop.get('order_id'),
            "customer_name": customer_data.get('name'),
            "address": customer_data.get('address'),
            "city": customer_data.get('city'),
            "state": customer_data.get('state'),
            "zip": customer_data.get('zip'),
            "lat": lat,
            "lon": lon,
            "notes": stop.get('notes'),
        })
    return pd.DataFrame(records)
