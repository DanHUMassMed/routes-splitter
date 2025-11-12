import re
import pandas as pd
from typing import Any, Dict, List, Union
from wulfs_routing_api.models.supabase_db import supabase
from wulfs_routing_api.models.stops.stop_model import StopModel
import logging

logger = logging.getLogger(__name__)

class SupabaseStop(StopModel):

    def create(self, item_to_insert: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """
        item_to_insert = {
                "route_id": new_route_id,
                "customer_id": customer_id_val,
                "order_id": order_id_val,
                "notes": stop_row.get("notes"),
            }
        """
        try:
            logger.debug(f"Inserting stop(s): {item_to_insert}")

            response = supabase.table('stops').insert(item_to_insert).execute()

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
            logger.info(f"Inserted {len(response.data)} stop(s) successfully.")

            # If we sent a Dict we expect a Dict back
            if isinstance(item_to_insert, dict):
                return response.data[0]
            return response.data

        except Exception as e:
            msg = f"Unexpected error during stop insert: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

    def get_stops_for_route(self, route_id):
        try:
            logger.error(f"Get Stops for Route: {route_id}")

            response = supabase.table('stops').select('*, customers(*)').eq('route_id', route_id).execute()

            if not response.data:
                return []

            # Successful get
            logger.info(f"Selected {len(response.data)} stops(s) successfully.")

            return response.data

        except Exception as e:
            msg = f"Unexpected error during select stops: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

        