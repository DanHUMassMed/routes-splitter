import math
from typing import Tuple
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import logging

import pandas as pd

logger = logging.getLogger(__name__)

class VRPService():
    def __init__(self):
        pass

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371  # km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return int(R * c * 1000)  # return in meters as integer


    def _split_sweep(self,df: pd.DataFrame, k: int, depot: Tuple[float,float]) -> np.ndarray:
        dlat, dlon = depot
        def angle(row):
            return np.arctan2(row["lat"]-dlat, (row["lon"]-dlon)*np.cos(np.radians((row["lat"]+dlat)/2)))
        
        # Calculate angles for all points
        df_angles = df.copy()
        df_angles["angle"] = df_angles.apply(angle, axis=1)
        
        # Sort by angle
        df_sorted = df_angles.sort_values(by="angle")
        
        labels = np.empty(len(df), dtype=int)
        
        # Assign customers to drivers in a round-robin fashion after sorting by angle
        # This aims for better initial balance and maintains angular contiguity
        for i in range(len(df_sorted)):
            # Use .loc for setting values by index, ensuring original index is preserved
            original_idx = df_sorted.index[i] # Get the original index from the sorted DataFrame
            labels[original_idx] = i % k # Assign based on original index

        # The original rebalancing logic can still be useful for fine-tuning
        # However, with round-robin assignment, the initial balance should be much better.
        # I will keep the rebalancing for now, but it might be less critical.
        
        # Quick rebalance (from original code, kept for fine-tuning)
        for _ in range(len(df) * k):
            counts = np.bincount(labels, minlength=k)
            while counts.max()-counts.min()>1:
                hi=int(np.argmax(counts)); lo=int(np.argmin(counts))
                hi_idxs=np.where(labels==hi)[0]
                lo_mean=np.mean(df_angles.loc[np.where(labels==lo)[0], "angle"]) if counts[lo]>0 else np.mean(df_angles["angle"])
                cand=min(hi_idxs, key=lambda i: abs(df_angles.loc[i, "angle"]-lo_mean))
                labels[cand]=lo; counts[hi]-=1; counts[lo]+=1

        return labels


    def solve_vrp(self, df: pd.DataFrame, num_drivers: int, depot_coords: Tuple[float, float]):
        logger.debug("Starting OR-Tools VRP solver...")

        # 1. Create the data model
        data = {}
        # Add depot to the locations
        locations = [(depot_coords[1], depot_coords[0])] + list(zip(df["lat"], df["lon"])) # (lat, lon)
        data["locations"] = locations
        data["num_vehicles"] = num_drivers
        data["depot"] = 0  # Depot is the first location in the list

        # 2. Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(
            len(data["locations"]), data["num_vehicles"], data["depot"]
        )

        # 3. Create Routing Model
        routing = pywrapcp.RoutingModel(manager)

        # 4. Define distance callback
        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            loc1 = data["locations"][from_node]
            loc2 = data["locations"][to_node]
            dist_km = self._haversine_distance(loc1[0], loc1[1], loc2[0], loc2[1])
            return int(dist_km * 1000)

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)

        # 5. Define cost of each arc
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # 6. Add Distance constraint (optional, but good for balancing)
        dimension_name = "Distance"
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            3000,  # vehicle maximum travel distance (arbitrary large number for now)
            True,  # start cumul to zero
            dimension_name,
        )
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100) # Encourage balanced distances

        # 7. Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(5) # Limit search time to 5 seconds

        # 8. Solve the problem
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            logger.debug("OR-Tools VRP solver failed to find a solution.")
            # Fallback to sweep if VRP fails
            labels = self._split_sweep(df, num_drivers, depot_coords)
            sequences = {i: list(range(len(df))) for i in range(num_drivers)}
            return labels, sequences

        # 9. Extract the solution
        labels = np.zeros(len(df), dtype=int)
        sequences = {i: [] for i in range(num_drivers)}

        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            route_distance = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index != data["depot"]:
                    # Assign customer to this driver
                    # node_index - 1 because depot is at index 0 in locations, but not in df
                    labels[node_index - 1] = vehicle_id
                    sequences[vehicle_id].append(node_index - 1)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            # Add depot as the last stop for sequencing
            sequences[vehicle_id].append(data["depot"])

        logger.info("OR-Tools VRP solver found a solution.")
        return labels, sequences
