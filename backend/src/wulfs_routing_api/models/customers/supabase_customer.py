import re
from shapely import wkb
import pandas as pd
from wulfs_routing_api.models.supabase_db import supabase
from wulfs_routing_api.models.customers.customer_model import CustomerModel

class SupabaseCustomer(CustomerModel):
    def get_all_customers(self) -> pd.DataFrame:
        response = supabase.table('customers').select("id, name_key, name, address, city, state, zip, location").execute()
        customer_df = pd.DataFrame(response.data)
        # Parse PostGIS location into lat/lon columns
        lons, lats = zip(*customer_df['location'].apply(self._parse_point))
        customer_df['lon'] = lons
        customer_df['lat'] = lats
        customer_df = customer_df.rename(columns={"id": "customer_id", "name": "customer_name"})

        return customer_df
    
    def _parse_point(self, point_data):
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