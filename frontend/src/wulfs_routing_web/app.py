import streamlit as st
import time

from wulfs_routing_web.state.session import init_session_state
from wulfs_routing_web.services.route_service import get_job_status, get_route_results
from wulfs_routing_web.services.api_client import APIError
from wulfs_routing_web.components.route_form import render_route_form
from wulfs_routing_web.components.results_viewer import render_results_viewer
from wulfs_routing_web.components.samsara_uploader import render_samsara_uploader
from wulfs_routing_web.components.history_sidebar import render_history_sidebar

# --- App Initialization ---
st.set_page_config(layout="wide", page_title="Wulf's Routing Automation")
init_session_state()

# --- Main App Layout ---
st.title("🚚 Wulf's Routing Automation")
main_col, history_col = st.columns([3, 1])

with main_col:
    render_route_form()

    # --- Job Monitoring & Result Fetching ---
    job_id = st.session_state.get('job_id')
    # Only poll if we have a job_id but no results yet
    if job_id and st.session_state.get('all_routes_df') is None:
        polling_placeholder = st.empty()
        with polling_placeholder.container():
            st.info("🔄 Processing routes...")
            
            while st.session_state.get('job_status') not in ["SUCCESS", "FAILURE"]:
                try:
                    status_data = get_job_status(job_id)
                    st.session_state['job_status'] = status_data.get('status')
                    
                    if status_data.get('status') == "RUNNING":
                        st.info(f"🔄 {status_data.get('message', 'Processing routes...')}")
                    
                    if st.session_state.get('job_status') in ["SUCCESS", "FAILURE"]:
                        break
                    time.sleep(2)
                except APIError as e:
                    st.error(f"Error checking job status: {e}")
                    st.session_state['job_status'] = "ERROR"
                    break
        
        polling_placeholder.empty()

        # --- Result Fetching ---
        if st.session_state.get('job_status') == "SUCCESS":
            with st.spinner("Task complete! Fetching results..."):
                try:
                    all_routes_df, missing_orders_df, map_path = get_route_results(job_id)
                    st.session_state['all_routes_df'] = all_routes_df
                    st.session_state['missing_orders_df'] = missing_orders_df
                    st.session_state['map_path'] = map_path
                    st.rerun() # Rerun to display the results viewer
                except APIError as e:
                    st.error(f"Error fetching results: {e}")
        
        elif st.session_state.get('job_status') in ["FAILURE", "ERROR"]:
             st.error("The background task failed. Please check the Celery worker terminal for more details.")

    # --- Display Area ---
    if st.session_state.get('all_routes_df') is not None:
        render_results_viewer()
        render_samsara_uploader()

with history_col:
    render_history_sidebar()