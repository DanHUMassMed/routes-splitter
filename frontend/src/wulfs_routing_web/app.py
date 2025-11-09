import numpy as np
import streamlit as st
import pandas as pd
import os
import datetime as dt
import requests
import time
import re
import tempfile
from datetime import datetime
from constants import API_URL, HQ_COORDINATES

from temp_package.route_publisher import save_routes_map, samsara_upload_unsequenced, export_assignments, HAVE_SK
from utils.data_processing import process_routes_from_api
from utils.api_client import api_get, api_post, APIError

import debugpy

# # Listen on port 5678
# debugpy.listen(("0.0.0.0", 5678))
# print("Waiting for debugger to attach...")
# debugpy.wait_for_client()  # Pause here until debugger attaches

# --- Streamlit App ----

# --- Session State Initialization ---
def init_session_state():
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

init_session_state()

# --- Main App Layout ---
st.set_page_config(layout="wide", page_title="Wulf's Routing Automation")
st.title("🚚 Wulf's Routing Automation")

main_col, history_col = st.columns([3, 1])

with main_col:
    st.markdown("Upload your daily orders file to generate optimized driver routes. The system will process them in the background.")

    # --- UI Components ---
    st.header("1. Upload Daily Orders")
    orders_file = st.file_uploader("Upload Daily Orders (Excel or CSV)", type=["xlsx", "xls", "csv"])

    st.header("2. Configure Routes")
    num_drivers = st.selectbox("Number of Drivers", options=list(range(1, 11)), index=3)
    split_mode = st.selectbox("Route Assignment Algorithm", ("kmeans", "sweep"))
    if split_mode == "kmeans" and not HAVE_SK:
        st.warning("Scikit-learn is not installed. Falling back to 'sweep' algorithm.")
        split_mode = "sweep"
    route_date = st.date_input("Route Date", value=st.session_state['route_date'], format="MM/DD/YYYY")

    # --- Job Execution ---
    st.header("3. Generate Routes")
    if st.button("Generate New Routes"):
        if orders_file is None:
            st.error("Please upload the Daily Orders file.")
        else:
            # Reset state
            for key in ['job_id', 'job_status', 'all_routes_df', 'missing_orders_df', 'map_path', 'loaded_route_id']:
                st.session_state[key] = None
            
            files = {'orders_file': (orders_file.name, orders_file.getvalue(), orders_file.type)}
            data = {"num_drivers": num_drivers, 
                    "split_mode": split_mode, 
                    "route_date_str": route_date.strftime('%Y-%m-%d'), 
                    "hq_lat": st.session_state['hq_lat'], 
                    "hq_lon": st.session_state['hq_lon']}
            try:
                response = requests.post(f"{API_URL}/routes/generate", files=files, data=data, timeout=10)
                response.raise_for_status()
                st.session_state['job_id'] = response.json()['job_id']
                st.session_state['route_date'] = route_date
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to start job: {e}")

    # --- Job Monitoring & Result Fetching ---
    if st.session_state['job_id'] and st.session_state['all_routes_df'] is None:
        # Polling logic
        spinner_placeholder = st.empty()
        spinner_placeholder.info("🔄 Processing routes...")
        
        while st.session_state.get('job_status') not in ["SUCCESS", "FAILURE"]:
            try:
                status_response = requests.get(f"{API_URL}/routes/status/{st.session_state['job_id']}", timeout=5)
                status_response.raise_for_status()
                status_data = status_response.json()
                st.session_state['job_status'] = status_data['status']
                if status_data['status'] == "RUNNING":
                    spinner_placeholder.info(f"{status_data.get('message', 'Processing routes....')}")

                if status_data['status'] in ["SUCCESS", "FAILURE"]:
                    break
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                st.error(f"Error checking job status: {e}")
                st.session_state['job_status'] = "ERROR"
                break
        
        # Fetch results once job is done
        if st.session_state.get('job_status') == "SUCCESS":
            st.success("Task complete! Fetching results...")
            try:
                result_response = requests.get(f"{API_URL}/routes/result/{st.session_state['job_id']}", timeout=10)
                result_response.raise_for_status()
                result_payload = result_response.json()['result']

                # IMPORTANT: Check for business logic failure inside the successful task
                if result_payload.get('status') == 'FAILURE':
                    st.error(f"Route generation failed: {result_payload.get('error_message', 'Unknown error')}")
                else:
                    st.session_state['missing_orders_df'] = pd.read_json(result_payload['missing_orders_json'], orient='split')
                    st.session_state['map_path'] = result_payload['map_path']
                    
                    all_stops = []
                    for route_id in result_payload['route_ids']:
                        route_detail_res = requests.get(f"{API_URL}/routes/{route_id}", timeout=10)
                        route_detail_res.raise_for_status()
                        all_stops.extend(route_detail_res.json())
                    
                    st.session_state['all_routes_df'] = process_routes_from_api(all_stops)
                    st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching results: {e}")
        elif st.session_state.get('job_status') == "FAILURE":
             st.error("The background task failed. Please check the Celery worker terminal for more details.")

    # --- Display Area ---
    if st.session_state['all_routes_df'] is not None:
        st.header("4. Review and Download Routes")
        if st.session_state['loaded_route_id']:
            st.info(f"Displaying historical route ID: {st.session_state['loaded_route_id']}")

        if not st.session_state['missing_orders_df'].empty:
            st.warning(f"⚠️ {len(st.session_state['missing_orders_df'])} orders not matched by name.")
            st.dataframe(st.session_state['missing_orders_df'])

        if st.session_state['map_path'] and os.path.exists(st.session_state['map_path']):
            with open(st.session_state['map_path'], "r") as f:
                st.components.v1.html(f.read(), height=500)
        
        st.subheader("Download Driver Routes")
        with tempfile.TemporaryDirectory() as tmpdir_download:
            # Safely get the column as a NumPy array
            all_routes_df = st.session_state.get('all_routes_df')
            if all_routes_df is not None and not all_routes_df.empty:

                if all_routes_df is not None and "driver_index" in all_routes_df.columns:
                    driver_indices = all_routes_df["driver_index"].to_numpy()
                else:
                    driver_indices = np.array([])  # empty array as fallback

                # Safe retrieval
                route_date = st.session_state.get('route_date')

                if isinstance(route_date, datetime):
                    route_date_str = route_date.strftime('%Y-%m-%d')
                else:
                    route_date_str = None  # or provide a default string, e.g., '1970-01-01'


                export_assignments(all_routes_df, 
                                driver_indices, 
                                tmpdir_download, 
                                st.session_state['route_date'].strftime('%Y-%m-%d'))
                
                for f in os.listdir(tmpdir_download):
                    if f.startswith("driver") and f.endswith(".csv"):
                        with open(os.path.join(tmpdir_download, f), "rb") as file_bytes:
                            st.download_button(f"Download {f}", file_bytes, f, "text/csv")

        st.header("5. Upload to Samsara")
        # Check if the API token is available
        samsara_token = os.getenv("SAMSARA_API_TOKEN")
        if not samsara_token or samsara_token == "":
            st.warning("SAMSARA_API_TOKEN environment variable not set. Cannot upload to Samsara.")
        elif st.session_state['all_routes_df'] is not None:
            st.subheader("Samsara Upload Configuration")
            route_start_time = st.time_input("Route Start Time", value=dt.time(7, 0))

            if st.button("Upload All Routes to Samsara"):
                with st.spinner("Uploading to Samsara..."):
                    try:
                        all_routes = st.session_state['all_routes_df']
                        route_date_str = st.session_state['route_date'].strftime('%Y-%m-%d')
                        start_local = dt.datetime.combine(st.session_state['route_date'], route_start_time)
                        
                        for driver_index in sorted(all_routes["driver_index"].unique()):
                            df_driver = all_routes[all_routes["driver_index"] == driver_index]
                            route_name = f"Deliveries {route_date_str} - Driver {driver_index + 1}"
                            
                            samsara_upload_unsequenced(
                                df_driver=df_driver,
                                token=samsara_token,
                                route_name=route_name,
                                depot_lat=st.session_state['hq_lat'],
                                depot_lon=st.session_state['hq_lon'],
                                start_local=start_local
                            )
                            st.success(f"Successfully uploaded route for Driver {driver_index + 1}")
                    except Exception as e:
                        st.error(f"Samsara upload failed: {e}")

# --- History Sidebar ---
with history_col:
    st.header("6. Historical Routes")
    try:
        history_res = requests.get(f"{API_URL}/routes", timeout=10)
        historical_routes = api_get(endpoint="routes")
        if not historical_routes:
            st.write("No past routes found.")
        else:
            for route in historical_routes:
                if st.button(f"Load Route ID: {route['id']} ({route['route_date']})"):
                    st.session_state['job_id'] = None
                    st.session_state['job_status'] = "SUCCESS"
                    st.session_state['loaded_route_id'] = route['id']
                    
                    # Fetch data for this historical route
                    
                    route_detail = api_get(endpoint=f"routes/{route['id']}")
                    st.session_state['all_routes_df'] = process_routes_from_api(route_detail)
                    st.session_state['route_date'] = dt.datetime.strptime(route['route_date'], '%Y-%m-%d').date()
                    map_date_str = st.session_state['route_date'].strftime('%Y-%m-%d')

                    # TODO this is non UI code and should be moved                    
                    # We don't have the original map path, but can regenerate it
                    temp_map_dir = os.path.join(os.getcwd(), "routes_out_temp_map")
                    os.makedirs(temp_map_dir, exist_ok=True)

                    sequences = {} #TODO Sequences is a required param but does not exists here?
                    save_routes_map(st.session_state['all_routes_df'], 
                                    temp_map_dir, 
                                    map_date_str, 
                                    (st.session_state['hq_lon'], st.session_state['hq_lat']),
                                    sequences
                                    )
                    st.session_state['map_path'] = os.path.join(temp_map_dir, f"routes_map_{map_date_str}.html")
                    st.rerun()
    except APIError as e:
        st.error(f"Could not fetch history: {e}")
