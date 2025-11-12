import streamlit as st
import datetime as dt
import os
import pandas as pd
from ..services.route_service import get_historical_routes, get_historical_route_details
from ..services.api_client import APIError
from ..utils.data_processing import process_routes_from_api
from ..utils.map_utils import generate_route_map

def render_history_sidebar():
    """Renders the sidebar for loading historical routes."""
    st.header("6. Historical Routes")
    try:
        historical_routes = get_historical_routes()
        if not historical_routes:
            st.write("No past routes found.")
            return

        # Sort routes by date, newest first
        historical_routes.sort(key=lambda r: r['route_date'], reverse=True)

        # Create a container with a fixed height to make the list scrollable
        history_container = st.container(height=600)
        with history_container:
            for route in historical_routes:
                button_label = f"Load Route ID: {route['id']} ({route['route_date']})"
                if st.button(button_label, key=f"load_route_{route['id']}"):
                    with st.spinner(f"Loading route {route['id']}..."):
                        # Reset state
                        st.session_state['job_id'] = None
                        st.session_state['job_status'] = "SUCCESS"
                        st.session_state['loaded_route_id'] = route['id']
                        
                        # Fetch and process data
                        route_detail = get_historical_route_details(route['id'])
                        all_routes_df = process_routes_from_api(route_detail)
                        st.session_state['all_routes_df'] = all_routes_df
                        
                        route_date = dt.datetime.fromisoformat(route['route_date']).date()
                        st.session_state['route_date'] = route_date
                        
                        # Regenerate map
                        temp_map_dir = "routes_out_temp_map" # Relative to where the app runs
                        map_path = generate_route_map(
                            df=all_routes_df,
                            outdir=temp_map_dir,
                            route_date=route_date.strftime('%Y-%m-%d'),
                            depot_coords=(st.session_state['hq_lon'], st.session_state['hq_lat']),
                            sequences={}
                        )
                        st.session_state['map_path'] = map_path
                        
                        # Clear missing orders as they aren't stored/relevant for historical views
                        st.session_state['missing_orders_df'] = pd.DataFrame()
                        
                        st.rerun()

    except APIError as e:
        st.error(f"Could not fetch history: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
