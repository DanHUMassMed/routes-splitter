import io
import pandas as pd
from .api_client import api_get, api_post, APIError
from ..utils.data_processing import process_routes_from_api
import logging
logger = logging.getLogger()

def start_route_generation(orders_file, num_vehicles, split_mode, route_date, hq_lat, hq_lon):
    """Starts the route generation job on the backend."""
    files = {'orders_file': (orders_file.name, orders_file.getvalue(), orders_file.type)}
    logger.error(f"NOT REALLY {orders_file.name} {orders_file.type}")
    data = {
        "num_vehicles": num_vehicles,
        "split_mode": split_mode,
        "route_date_str": route_date.strftime('%Y-%m-%d'),
        "hq_lat": hq_lat,
        "hq_lon": hq_lon
    }
    response = api_post("routes/generate", files=files, data=data)
    return response.get('job_id')

def get_job_status(job_id):
    """Gets the status of a running job."""
    return api_get(f"routes/{job_id}/status")

def get_route_results(job_id):
    """Gets the results of a completed job."""
    result_payload = api_get(f"routes/{job_id}/results")['result']

    if result_payload.get('status') == 'FAILURE':
        raise APIError(f"Route generation failed: {result_payload.get('error_message', 'Unknown error')}")

    missing_orders_json = io.StringIO(result_payload['missing_orders_json'])
    missing_orders_df = pd.read_json(missing_orders_json, orient='split')
    map_path = result_payload['map_path']

    all_stops = []
    for route_id in result_payload['route_ids']:
        # In the original app, this was a direct requests call.
        # Refactoring to use the existing service function.
        route_detail = get_historical_route_details(route_id)
        all_stops.extend(route_detail)

    all_routes_df = process_routes_from_api(all_stops)
    
    return all_routes_df, missing_orders_df, map_path

def get_historical_routes():
    """Gets the list of historical routes."""
    return api_get("routes")

def get_historical_route_details(route_id):
    """Gets the details for a specific historical route."""
    return api_get(f"routes/{route_id}/stops")
