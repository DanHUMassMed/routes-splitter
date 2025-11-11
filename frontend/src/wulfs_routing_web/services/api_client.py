import requests
from ..constants import API_URL

class APIError(Exception):
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

def api_post(endpoint: str, files=None, data=None, timeout=10):
    try:
        res = requests.post(f"{API_URL}/{endpoint}", files=files, data=data, timeout=timeout)
        if res.status_code == 200:
            return res.json()
        else:
            raise APIError(f"POST {endpoint} returned {res.status_code}", res.status_code, res)
    except requests.RequestException as e:
        raise APIError(f"POST {endpoint} failed: {e}") from e

def api_get(endpoint: str, timeout=10):
    try:
        res = requests.get(f"{API_URL}/{endpoint}", timeout=timeout)
        if res.status_code == 200:
            return res.json()
        else:
            raise APIError(f"GET {endpoint} returned {res.status_code}", res.status_code, res)
    except requests.RequestException as e:
        raise APIError(f"GET {endpoint} failed: {e}") from e