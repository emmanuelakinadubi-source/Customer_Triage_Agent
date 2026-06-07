import os
from typing import Any, Dict, List

import requests


API_URL = os.getenv("API_URL", "http://backend:8000")


def post_triage_batch(messages: List[str]) -> List[Dict[str, Any]]:
    """Send multiple messages to the triage API and return results."""
    payload = {"messages": messages}
    response = requests.post(f"{API_URL}/triage/batch", json=payload)
    response.raise_for_status()
    return response.json()

