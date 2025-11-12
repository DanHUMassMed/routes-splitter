import math
from typing import Dict, List, Tuple
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import logging

import pandas as pd

logger = logging.getLogger(__name__)

class VRPService():
    def __init__(self):
        pass

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
        
        # Assign customers to vehicles in a round-robin fashion after sorting by angle
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

    def build_vehicle_routes_from_labels(self,
        vehicle_labels: np.ndarray,
        stops_table: pd.DataFrame,
        num_vehicles: int,
        depot_location: Tuple[float, float],
        lat_column: str = "lat",
        lon_column: str = "lon",
    ) -> Dict[int, List[int]]:
        """
        Construct per-vehicle route sequences using a greedy nearest-neighbor heuristic.

        Args:
            vehicle_labels: np.ndarray
                Array of length N (number of stops). Each element assigns a stop index to a vehicle (0..num_vehicles-1).
            stops_table: pd.DataFrame
                DataFrame containing stop coordinates with columns specified by `lat_column` and `lon_column`.
            num_vehicles: int
                Number of vehicles (or routes).
            depot_location: Tuple[float, float]
                (latitude, longitude) coordinates for the depot.
            lat_column: str, default="lat"
                Name of the latitude column in the stops table.
            lon_column: str, default="lon"
                Name of the longitude column in the stops table.

        Returns:
            Dict[int, List[int]]
                Dictionary mapping each vehicle index to a list of stop indices
                representing their route order (greedy nearest-neighbor from depot).
        """

        # Create lookup for coordinates
        coords_lookup = {
            idx: (row[lat_column], row[lon_column])
            for idx, row in stops_table.reset_index(drop=True).iterrows()
        }

        def greedy_route(stop_indices: List[int], start_coord: Tuple[float, float]) -> List[int]:
            """Return a greedy nearest-neighbor sequence for assigned stops."""
            if not stop_indices:
                return []
            unvisited = set(stop_indices)
            route = []
            current_coord = start_coord
            while unvisited:
                nearest_stop = min(unvisited, key=lambda i: self.compute_haversine_distance(current_coord, coords_lookup[i]))
                route.append(nearest_stop)
                unvisited.remove(nearest_stop)
                current_coord = coords_lookup[nearest_stop]
            return route

        # Build routes per vehicle
        vehicle_routes = {}
        for vehicle_id in range(num_vehicles):
            assigned_stops = [i for i, label in enumerate(vehicle_labels) if label == vehicle_id]
            vehicle_routes[vehicle_id] = greedy_route(assigned_stops, depot_location)

        return vehicle_routes

    # ---------------------------------------------------------------------
    # Haversine distance
    # ---------------------------------------------------------------------
    def compute_haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Compute great-circle distance (km) between two lat/lon coordinates."""
        R = 6371.0  # Earth radius in km
        lat1, lon1 = map(math.radians, coord1)
        lat2, lon2 = map(math.radians, coord2)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        return 2 * R * math.asin(math.sqrt(a))


    # ---------------------------------------------------------------------
    # Compute full distance matrix including depot
    # ---------------------------------------------------------------------
    def build_distance_matrix(self, stops_table: pd.DataFrame, depot_location: Tuple[float, float]) -> List[List[float]]:
        """Build distance matrix in km including depot as index 0."""
        coords = [(row["lat"], row["lon"]) for _, row in stops_table.iterrows()]
        all_points = [depot_location] + coords
        return [[self.compute_haversine_distance(a, b) for b in all_points] for a in all_points]


    # ---------------------------------------------------------------------
    # Estimate max route distance dynamically
    # ---------------------------------------------------------------------
    def estimate_max_route_distance(self, distance_matrix: List[List[float]], num_vehicles: int, safety_factor: float = 1.3) -> int:
        """Estimate reasonable maximum route distance per vehicle (meters)."""
        flat_distances = [d for i, row in enumerate(distance_matrix) for j, d in enumerate(row) if j > i]
        max_pairwise_km = max(flat_distances)
        max_distance_m = int(max_pairwise_km * 1000 * (num_vehicles + 1) / num_vehicles * safety_factor)
        print(f"Estimated max route distance per vehicle: {max_distance_m / 1000:.1f} km")
        return max_distance_m


    # ---------------------------------------------------------------------
    # Compute per-vehicle capacity dynamically
    # ---------------------------------------------------------------------
    def estimate_vehicle_capacity(self, num_stops: int, num_vehicles: int) -> int:
        """Compute per-vehicle capacity to ensure all vehicles are used."""
        return math.ceil(num_stops / num_vehicles)


    # ---------------------------------------------------------------------
    # Register distance dimension (max route length & balancing)
    # ---------------------------------------------------------------------
    def add_distance_dimension(self, routing: pywrapcp.RoutingModel, transit_callback_index: int, max_distance_m: int) -> None:
        """Add distance dimension with max per vehicle and global span cost."""
        routing.AddDimension(
            transit_callback_index,
            0,  # slack
            max_distance_m,
            True,  # start cumul to zero
            "Distance"
        )
        routing.GetDimensionOrDie("Distance").SetGlobalSpanCostCoefficient(100)


    # ---------------------------------------------------------------------
    # Register capacity dimension (dummy to force all vehicles)
    # ---------------------------------------------------------------------
    def add_capacity_dimension(self, routing: pywrapcp.RoutingModel, manager: pywrapcp.RoutingIndexManager,
                            num_stops: int, num_vehicles: int) -> None:
        """Add vehicle capacity dimension to force all vehicles to be assigned."""
        demands = [1] * num_stops  # each stop counts as 1 unit
        vehicle_capacity = self.estimate_vehicle_capacity(num_stops, num_vehicles)

        def demand_callback(from_index: int) -> int:
            node = manager.IndexToNode(from_index)
            if node == 0:  # depot
                return 0
            return demands[node - 1]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # slack
            [vehicle_capacity] * num_vehicles,
            True,  # start cumul to zero
            "Capacity"
        )


    # ---------------------------------------------------------------------
    # Register distance (cost) callback
    # ---------------------------------------------------------------------
    def register_distance_callback(self, routing: pywrapcp.RoutingModel, manager: pywrapcp.RoutingIndexManager,
                                distance_matrix: List[List[float]]) -> int:
        """Register the distance callback and set as arc cost evaluator."""
        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # meters

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        return transit_callback_index


    def solve_vrp(self, split_mode, stops_table: pd.DataFrame, num_vehicles: int,
                                depot_location: Tuple[float, float]) -> Tuple[np.ndarray, Dict[int, List[int]]]:
        if split_mode=="OR-Tool":
            return self.solve_vrp_or_tools(stops_table, num_vehicles, depot_location)
        elif split_mode=="Sweep":
            labels = self._split_sweep(stops_table, num_vehicles, depot_location)
            vehicle_routes = self.build_vehicle_routes_from_labels(labels, stops_table, num_vehicles, depot_location)
            return labels, vehicle_routes
        else:
            raise RuntimeError("Error on Solver type must be (OR-Tools or Sweep)")


    # ---------------------------------------------------------------------
    # Solve VRP with OR-Tools
    # ---------------------------------------------------------------------
    def solve_vrp_or_tools(self, stops_table: pd.DataFrame, num_vehicles: int,
                                depot_location: Tuple[float, float]) -> Tuple[np.ndarray, Dict[int, List[int]]]:
        """Solve multi-vehicle VRP with distance and capacity constraints, fallback to sweep+greedy."""
        num_stops = len(stops_table)
        distance_matrix = self.build_distance_matrix(stops_table, depot_location)

        # Manager and routing model
        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        # Register distance callback
        transit_callback_index = self.register_distance_callback(routing, manager, distance_matrix)

        # Add constraints
        #max_distance_m = estimate_max_route_distance(distance_matrix, num_vehicles)
        max_distance_m = int(1e9)  # temporarily unlimited
        self.add_distance_dimension(routing, transit_callback_index, max_distance_m)
        self.add_capacity_dimension(routing, manager, num_stops, num_vehicles)

        # Small fixed cost per vehicle to encourage usage
        for vehicle_id in range(num_vehicles):
            routing.SetFixedCostOfVehicle(100, vehicle_id)

        # Search parameters
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.seconds = 10

        # Solve
        print("🧩 Solving VRP with OR-Tools...")
        solution = routing.SolveWithParameters(search_params)

        # Extract solution
        if solution:
            labels = np.full(num_stops, -1, dtype=int)
            vehicle_routes: Dict[int, List[int]] = {}

            for vehicle_id in range(num_vehicles):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    node = manager.IndexToNode(index)
                    if node != 0:  # depot
                        stop_idx = node - 1
                        route.append(stop_idx)
                        labels[stop_idx] = vehicle_id
                    index = solution.Value(routing.NextVar(index))
                vehicle_routes[vehicle_id] = route
            return labels, vehicle_routes

        # Fallback
        print("⚠️ OR-Tools failed — using sweep + greedy fallback...")
        labels = self._split_sweep(stops_table, num_vehicles, depot_location)
        vehicle_routes = self.build_vehicle_routes_from_labels(labels, stops_table, num_vehicles, depot_location)
        return labels, vehicle_routes
