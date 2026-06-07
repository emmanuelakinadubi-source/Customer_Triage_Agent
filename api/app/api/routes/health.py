from fastapi import APIRouter

from ...schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}
