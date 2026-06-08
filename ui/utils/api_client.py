import os
from typing import Any, Dict, List

import requests

API_URL = os.getenv("API_URL", "http://api:8000")


def post_triage_single(message: str) -> Dict[str, Any]:
    """Send one message to POST /triage and return the TriageResponse dict."""
    response = requests.post(
        f"{API_URL}/triage",
        json={"message": message},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def post_triage_batch(messages: List[str]) -> List[Dict[str, Any]]:
    """Send multiple messages to POST /triage/batch."""
    response = requests.post(
        f"{API_URL}/triage/batch",
        json={"messages": messages},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def get_triage_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent triage records from GET /triage/history."""
    response = requests.get(
        f"{API_URL}/triage/history",
        params={"limit": limit},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
