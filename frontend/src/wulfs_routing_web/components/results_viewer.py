import streamlit as st
import os
import tempfile
from datetime import datetime
from ..utils.data_processing import export_assignments

def render_results_viewer():
    """Renders the UI for displaying route results, map, and download links."""
    st.header("4. Review and Download Routes")

    if st.session_state.get('loaded_route_id'):
        st.info(f"Displaying historical route ID: {st.session_state['loaded_route_id']}")

    missing_orders_df = st.session_state.get('missing_orders_df')
    if missing_orders_df is not None and not missing_orders_df.empty:
        st.warning(f"⚠️ {len(missing_orders_df)} orders not matched by name.")
        st.dataframe(missing_orders_df)

    map_path = st.session_state.get('map_path')
    if map_path and os.path.exists(map_path):
        with open(map_path, "r", encoding="utf-8") as f:
            st.components.v1.html(f.read(), height=500)
    
    st.subheader("Download Vehicle Routes")
    all_routes_df = st.session_state.get('all_routes_df')

    if all_routes_df is not None and not all_routes_df.empty:
        with tempfile.TemporaryDirectory() as tmpdir_download:
            route_date = st.session_state.get('route_date')
            
            if hasattr(route_date, 'strftime'):
                route_date_str = route_date.strftime('%Y-%m-%d')
            else:
                route_date_str = datetime.now().strftime('%Y-%m-%d')

            export_assignments(
                routes_df=all_routes_df,
                outdir=tmpdir_download,
                route_date=route_date_str
            )
            
            download_files = sorted([f for f in os.listdir(tmpdir_download) if f.startswith("vehicle") and f.endswith(".csv")])
            
            cols = st.columns(len(download_files))
            for i, f in enumerate(download_files):
                with open(os.path.join(tmpdir_download, f), "rb") as file_bytes:
                    cols[i].download_button(
                        label=f"Download {f}",
                        data=file_bytes,
                        file_name=f,
                        mime="text/csv"
                    )
