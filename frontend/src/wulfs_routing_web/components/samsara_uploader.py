import streamlit as st
import os
import datetime as dt
from ..services.samsara_service import upload_routes_to_samsara
from ..utils.env_utils import get_env

def render_samsara_uploader():
    """Renders the UI for uploading routes to Samsara."""
    st.header("5. Upload to Samsara")

    samsara_token = get_env("SAMSARA_API_TOKEN")
    if not samsara_token:
        st.warning("SAMSARA_API_TOKEN environment variable not set. Cannot upload to Samsara.")
        return

    st.subheader("Samsara Upload Configuration")
    route_start_time = st.time_input("Route Start Time", value=dt.time(7, 0))

    if st.button("Upload All Routes to Samsara"):
        all_routes = st.session_state.get('all_routes_df')
        if all_routes is None or all_routes.empty:
            st.warning("No routes to upload.")
            return

        with st.spinner("Uploading to Samsara..."):
            try:
                upload_generator = upload_routes_to_samsara(
                    all_routes_df=all_routes,
                    route_date=st.session_state['route_date'],
                    route_start_time=route_start_time,
                    hq_lat=st.session_state['hq_lat'],
                    hq_lon=st.session_state['hq_lon']
                )
                for message in upload_generator:
                    if "Successfully" in message:
                        st.success(message)
                    else:
                        st.warning(message)

            except ValueError as e:
                st.error(e)
            except Exception as e:
                st.error(f"An unexpected error occurred during Samsara upload: {e}")
