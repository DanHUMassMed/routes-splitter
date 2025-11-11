import os
import datetime as dt
import requests
import pandas as pd
from typing import Optional

from ..constants import SAMSARA_ROUTES_URL

def _samsara_upload_unsequenced(vehicle_df: pd.DataFrame, token: str, route_name: str,
                               depot_lat: float, depot_lon: float, start_local: dt.datetime,
                               vehicle_id: Optional[str] = None):
    """Helper function to upload a single vehicle's route to Samsara."""
    stops = [{
        "singleUseLocation": {"address":"Depot","latitude":depot_lat,"longitude":depot_lon},
        "scheduledDepartureTime": start_local.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")
    }]
    arrival_time = start_local
    for i, (_, r) in enumerate(vehicle_df.iterrows()):
        # Increment start time by 15 mins for each stop
        arrival_time = start_local + dt.timedelta(minutes=15 * (i + 1))
        stops.append({
            "singleUseLocation": {
                "address": f'{r["address"]}, {r["city"]}, {r["state"]} {r["zip"]}',
                "latitude": float(r["lat"]),
                "longitude": float(r["lon"])
            },
            "scheduledArrivalTime": arrival_time.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "notes": str(r.get("notes",""))[:2000]
        })

    # Add final stop to return to depot
    final_arrival_time = arrival_time + dt.timedelta(minutes=15)
    stops.append({
        "singleUseLocation": {"address": "Depot", "latitude": depot_lat, "longitude": depot_lon},
        "scheduledArrivalTime": final_arrival_time.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    })
    payload = {
        "name": route_name,
        "stops": stops,
        "settings": {
            "routeStartingCondition":"departFirstStop",
            "routeCompletionCondition":"arriveLastStop"
        }
    }
    if vehicle_id:
        payload["driverId"] = str(vehicle_id)
    
    headers = {"Authorization": f'Bearer {token}', "Content-Type":"application/json"}
    r = requests.post(SAMSARA_ROUTES_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def upload_routes_to_samsara(all_routes_df: pd.DataFrame, route_date: dt.date, route_start_time: dt.time, hq_lat: float, hq_lon: float):
    """
    Uploads all vehicle routes from a DataFrame to Samsara.
    
    Yields: A success or error message for each vehicle.
    """
    samsara_token = os.getenv("SAMSARA_API_TOKEN")
    if not samsara_token:
        raise ValueError("SAMSARA_API_TOKEN environment variable not set.")

    start_local = dt.datetime.combine(route_date, route_start_time)
    route_date_str = route_date.strftime('%Y-%m-%d')

    for vehicle_index in sorted(all_routes_df["vehicle_index"].unique()):
        try:
            vehicle_df = all_routes_df[all_routes_df["vehicle_index"] == vehicle_index]
            route_name = f"Deliveries {route_date_str} - Vehicle {vehicle_index + 1}"
            
            _samsara_upload_unsequenced(
                vehicle_df=vehicle_df,
                token=samsara_token,
                route_name=route_name,
                depot_lat=hq_lat,
                depot_lon=hq_lon,
                start_local=start_local
            )
            yield f"Successfully uploaded route for Vehicle {vehicle_index + 1}"
        except Exception as e:
            yield f"Failed to upload for Vehicle {vehicle_index + 1}: {e}"
