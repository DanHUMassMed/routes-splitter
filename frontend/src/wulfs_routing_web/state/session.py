import streamlit as st
import datetime as dt
from wulfs_routing_web.constants import HQ_COORDINATES

# --- Session State Initialization ---
def init_session_state():
    """Initializes the session state with default values."""
    defaults = {
        'upload_status': '',
        'job_id': None,
        'job_status': None,
        'all_routes_df': None,
        'missing_orders_df': None,
        'route_date': dt.date.today(),
        'hq_lat': HQ_COORDINATES.lat,
        'hq_lon': HQ_COORDINATES.lon,
        'map_path': None,
        'loaded_route_id': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
