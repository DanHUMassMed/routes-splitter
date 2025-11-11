import streamlit as st
from ..services.route_service import start_route_generation
from ..services.api_client import APIError

def render_route_form():
    """Renders the UI for uploading orders, configuring, and generating routes."""
    st.markdown("Upload your daily orders file to generate optimized vehicle routes. The system will process them in the background.")

    st.header("1. Upload Daily Orders")
    orders_file = st.file_uploader("Upload Daily Orders (Excel or CSV)", type=["xlsx", "xls", "csv"])

    st.header("2. Configure Routes")
    num_vehicles = st.selectbox("Number of Vehicles", options=list(range(1, 11)), index=3)
    split_mode = st.selectbox("Route Assignment Algorithm", ("kmeans", "sweep"))
    route_date = st.date_input("Route Date", value=st.session_state.get('route_date'), format="MM/DD/YYYY")

    st.header("3. Generate Routes")
    if st.button("Generate New Routes"):
        if orders_file is None:
            st.error("Please upload the Daily Orders file.")
            st.stop()

        # Reset state for a new job
        for key in ['job_id', 'job_status', 'all_routes_df', 'missing_orders_df', 'map_path', 'loaded_route_id']:
            st.session_state[key] = None
        
        with st.spinner("Starting route generation job..."):
            try:
                job_id = start_route_generation(
                    orders_file=orders_file,
                    num_vehicles=num_vehicles,
                    split_mode=split_mode,
                    route_date=route_date,
                    hq_lat=st.session_state['hq_lat'],
                    hq_lon=st.session_state['hq_lon']
                )
                if job_id:
                    st.session_state['job_id'] = job_id
                    st.session_state['route_date'] = route_date
                    st.rerun()
                else:
                    st.error("Failed to get job ID from the server.")
            except APIError as e:
                st.error(f"Failed to start job: {e}")
