import os
from typing import Any, Dict, List

import requests

API_URL = os.getenv("API_URL", "http://api:8000")


class APIError(Exception):
    """Raised when the API returns a non-2xx response."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _raise_api_error(response: requests.Response) -> None:
    """Extract the human-readable detail from an error response and raise APIError."""
    if response.ok:
        return
    try:
        body = response.json()
        detail = body.get("detail", "")
        # Pydantic validation errors come as a list of error objects
        if isinstance(detail, list):
            detail = "; ".join(e.get("msg", str(e)) for e in detail)
    except Exception:
        detail = response.text or ""
    if not detail:
        detail = f"Server returned status {response.status_code}"
    raise APIError(status_code=response.status_code, detail=detail)


def post_triage_single(message: str) -> Dict[str, Any]:
    response = requests.post(
        f"{API_URL}/triage",
        json={"message": message},
        timeout=60,
    )
    _raise_api_error(response)
    return response.json()


def post_triage_batch(messages: List[str]) -> List[Dict[str, Any]]:
    response = requests.post(
        f"{API_URL}/triage/batch",
        json={"messages": messages},
        timeout=120,
    )
    _raise_api_error(response)
    return response.json()


def get_triage_history(limit: int = 50) -> List[Dict[str, Any]]:
    response = requests.get(
        f"{API_URL}/triage/history",
        params={"limit": limit},
        timeout=30,
    )
    _raise_api_error(response)
    return response.json()
