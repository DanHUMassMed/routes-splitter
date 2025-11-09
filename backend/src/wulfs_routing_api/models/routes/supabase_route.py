import re
from typing import Any, Dict, List, Union
import pandas as pd

from wulfs_routing_api.models.supabase_db import supabase
from wulfs_routing_api.models.routes.route_model import RouteModel
import logging

logger = logging.getLogger(__name__)

# TODO We do not have pydantic Objects yet. i.e., DTOs (Data Transfer Objects)
class SupabaseRoute(RouteModel):
    def create(self, item_to_insert: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """
        route_to_insert = {
            "route_date": route_date_str,
            "driver_index": int(driver_idx),
            "route_name": f"Deliveries {route_date_str} - Driver {driver_idx + 1}"
        }
        """
        try:
            logger.debug(f"Inserting route(s): {item_to_insert}")

            response = supabase.table("routes").insert(item_to_insert).execute()

            # Validate response
            if not hasattr(response, "data") or response.data is None:
                msg = f"Insert returned no data. Response: {response}"
                logger.error(msg)
                raise RuntimeError(msg)

            if not response.data:
                msg = f"Insert succeeded but empty response data. Payload: {item_to_insert}"
                logger.warning(msg)
                return [] if isinstance(item_to_insert, list) else None

            # Successful insert
            logger.info(f"Inserted {len(response.data)} route(s) successfully.")

            # If we sent a Dict we expect a Dict back
            if isinstance(item_to_insert, dict):
                return response.data[0]
            return response.data

        except Exception as e:
            msg = f"Unexpected error during route insert: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        