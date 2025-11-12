# Plan: Add Scrollbar to Frontend History Sidebar

**Objective:** To enhance the user experience of the Wulf's Routing Automation frontend by adding a vertical scrollbar to the "Historical Routes" sidebar component. This will ensure that a large number of historical routes are neatly contained within a fixed-height window, preventing the sidebar from becoming excessively long.

## 1. Analysis of the Current State

-   **File to Modify:** `frontend/src/wulfs_routing_web/components/history_sidebar.py`
-   **Relevant Function:** `render_history_sidebar()`
-   **Current Behavior:** The `render_history_sidebar` function fetches a list of all historical routes and iterates through them, creating a `st.button` for each one. If the number of routes is large, the sidebar will expand vertically to accommodate all the buttons, which can push other UI elements off-screen or create a poor layout.

## 2. Implementation Strategy

The most effective and idiomatic way to create a scrollable container in Streamlit is to use `st.container()` and assign it a fixed height. When the content within the container exceeds this height, Streamlit automatically adds a vertical scrollbar.

We will wrap the button-rendering loop inside a container with a predefined height.

## 3. Step-by-Step Implementation Plan

1.  **Navigate to the component file:**
    Open the file `frontend/src/wulfs_routing_web/components/history_sidebar.py` for editing.

2.  **Locate the rendering loop:**
    Inside the `render_history_sidebar` function, find the `for` loop that iterates over `historical_routes`.

    ```python
    # --- Current Code Snippet ---
    for route in historical_routes:
        button_label = f"Load Route ID: {route['id']} ({route['route_date']})"
        if st.button(button_label, key=f"load_route_{route['id']}"):
            # ... button click logic ...
    ```

3.  **Wrap the loop in a scrollable container:**
    Before the `for` loop, create a container using `st.container(height=300)`. The height can be adjusted, but 300 pixels is a reasonable starting point. All the button-rendering logic should be placed inside this container.

    ```python
    # --- New Code Snippet ---
    # Create a container with a fixed height to make the list scrollable
    history_container = st.container(height=300)

    with history_container:
        for route in historical_routes:
            button_label = f"Load Route ID: {route['id']} ({route['route_date']})"
            if st.button(button_label, key=f"load_route_{route['id']}"):
                # ... button click logic (remains unchanged) ...
    ```

4.  **Final Code Structure:**
    The updated `render_history_sidebar` function will look like this:

    ```python
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
            history_container = st.container(height=300)
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
                            temp_map_dir = "routes_out_temp_map"
                            map_path = generate_route_map(
                                df=all_routes_df,
                                outdir=temp_map_dir,
                                route_date=route_date.strftime('%Y-%m-%d'),
                                depot_coords=(st.session_state['hq_lon'], st.session_state['hq_lat']),
                                sequences={}
                            )
                            st.session_state['map_path'] = map_path
                            
                            st.session_state['missing_orders_df'] = pd.DataFrame()
                            
                            st.rerun()

        except APIError as e:
            st.error(f"Could not fetch history: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    ```

## 4. Verification

After applying the changes, run the Streamlit application. If there are enough historical routes to exceed the 300px height of the container, a vertical scrollbar should appear, allowing the user to scroll through the list without affecting the overall layout of the page.
