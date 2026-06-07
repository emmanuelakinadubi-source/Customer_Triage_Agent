from fastapi import APIRouter

from .health import router as health_router
from .triage import router as triage_router

router = APIRouter()
router.include_router(health_router)
router.include_router(triage_router)
