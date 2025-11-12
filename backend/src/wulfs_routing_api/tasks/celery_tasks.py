import os
import tempfile
import pandas as pd
import base64
import re
import time

import logging

from wulfs_routing_api.services.customer_service import CustomerService
from wulfs_routing_api.models.customers.supabase_customer import SupabaseCustomer
from wulfs_routing_api.services.order_services import OrderService
from wulfs_routing_api.models.orders.supabase_order import SupabaseOrder
from wulfs_routing_api.services.route_service import RouteService
from wulfs_routing_api.models.routes.supabase_route import SupabaseRoute
from wulfs_routing_api.services.stops_service import StopService
from wulfs_routing_api.models.stops.supabase_stop import SupabaseStop
from wulfs_routing_api.services.vrp_service import VRPService

from wulfs_routing_api.utils.data_io_utils import load_base64_to_df
from wulfs_routing_api.celery_app import celery_app
from wulfs_routing_api.models.supabase_db import supabase

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_routing_task(self, orders_file_content_b64: str, num_vehicles: int, split_mode: str, route_date_str: str, hq_lat: float, hq_lon: float):
    """
    Celery task to perform route generation and save results to Supabase.
    """
    if not supabase:
        raise ConnectionError("Supabase client not initialized. Check .env file.")

    self.update_state(state='PROGRESS', meta={'status': 'Starting...'}) 
    time.sleep(3)

    try:
        customer_service = CustomerService(SupabaseCustomer())
        order_service = OrderService(SupabaseOrder())
        route_service = RouteService(SupabaseRoute())
        stop_service = StopService(SupabaseStop())
        vrp_service = VRPService()

        # 1. Load uploaded orders file
        orders_df = load_base64_to_df(orders_file_content_b64)
        orders_df.to_csv("test.csv",index=False)
        logger.error("Can you see this error from celery")
        logger.debug("Can you see this debug from celery")

        # 2. Load master customer data from Supabase
        self.update_state(state='PROGRESS', meta={'status':'RUNNING','message': 'Fetching customer data from database...'})
        customer_df = customer_service.load_customer_master_data()

        # 3. Merge data
        self.update_state(state='PROGRESS', meta={'status':'RUNNING','message': 'Merging order data with customer data...'}) 
        stops_df, missing_orders = order_service.customer_details_for_orders(orders_df, customer_df)

        # 4. Assign routes using OR-Tools VRP solver
        self.update_state(state='PROGRESS', meta={'status':'RUNNING','message': 'Calculating routes with OR-Tools...'}) 
        labels, routes = vrp_service.solve_vrp(split_mode, stops_df, num_vehicles, (hq_lon, hq_lat))
        stops_df["vehicle_index"] = labels

        # 5. Save results to Supabase
        self.update_state(state='PROGRESS', meta={'status':'RUNNING','message': 'Saving results to database...'}) 
        route_id_map = route_service.persist_routes(stops_df, route_date_str)
        stop_service.persist_stops(stops_df, route_id_map)
        created_route_ids = list(route_id_map.values())

        # Save a map for the UI to display
        temp_map_dir = os.path.join(os.getcwd(), "routes_out_temp_map")
        os.makedirs(temp_map_dir, exist_ok=True)
        route_service.save_routes_map(stops_df, temp_map_dir, route_date_str, (hq_lon, hq_lat), routes)
        map_path = os.path.join(temp_map_dir, f"routes_map_{route_date_str}.html")

        return {
            "status": "SUCCESS",
            "route_ids": created_route_ids,
            "missing_orders_json": missing_orders.to_json(orient='split'),
            "map_path": map_path
        }

    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"Celery task failed: {e}\n{tb_str}")
        # Return a failure payload instead of raising or updating state
        return {
            "status": "FAILURE",
            "error_message": f"{e}\n{tb_str}"
        }