import requests
import time
from typing import Tuple, Optional, Dict

class OSRMService:
    def __init__(self, osrm_url: str = "http://localhost:5001", timeout: int = 5, max_retries: int = 3, retry_delay: float = 0.5):
        """
        OSRMService handles route distance and duration queries via a running OSRM server.

        Args:
            osrm_url (str): Base URL of the OSRM server.
            timeout (int): Request timeout in seconds.
            max_retries (int): Number of retry attempts for failed requests.
            retry_delay (float): Delay between retries in seconds.
        """
        self.osrm_url = osrm_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _validate_coords(self, coords: Tuple[float, float]) -> bool:
        """Ensure coordinates are valid (latitude -90..90, longitude -180..180)."""
        lat, lon = coords
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def get_route(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Optional[Dict]:
        """
        Fetch a route from OSRM server between two coordinates.
        Coordinates should be in (latitude, longitude) format.
        Returns route JSON on success, None on failure.
        """
        if not (self._validate_coords(start_coords) and self._validate_coords(end_coords)):
            print(f"Invalid coordinates: {start_coords}, {end_coords}")
            return None

        # OSRM expects coordinates in longitude,latitude order
        coordinates = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        url = f"{self.osrm_url}/route/v1/driving/{coordinates}"
        params = {"overview": "false"}

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                # Ensure routes exist
                if "routes" in data and len(data["routes"]) > 0:
                    return data
                else:
                    print(f"No route found between {start_coords} and {end_coords}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt}: Error fetching route: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    return None
            except ValueError as ve:
                print(f"Attempt {attempt}: Invalid JSON response: {ve}")
                return None

    @staticmethod
    def meters_to_miles(meters: float) -> float:
        """Convert meters to miles."""
        return float(meters) * 0.0006213711922373339

    def get_route_time_distance(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[Optional[float], Optional[float]]:
        """
        Returns (distance_miles, duration_seconds) for a route.
        Returns (None, None) if route could not be fetched.
        """
        route = self.get_route(start_coords, end_coords)
        if route and "routes" in route and len(route["routes"]) > 0:
            meters = route["routes"][0].get("distance")
            duration = route["routes"][0].get("duration")
            if meters is not None and duration is not None:
                return self.meters_to_miles(meters), duration
        return None, None

    def get_route_distance(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Optional[float]:
        """
        Returns route distance in miles.
        Returns None if route could not be fetched.
        """
        route = self.get_route(start_coords, end_coords)
        if route and "routes" in route and len(route["routes"]) > 0:
            meters = route["routes"][0].get("distance")
            if meters is not None:
                return self.meters_to_miles(meters)
        return None
