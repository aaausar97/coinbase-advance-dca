"""Health / status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.common import HealthOut


router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    settings = request.app.state.settings
    plans = getattr(request.app.state, "plans", []) or []
    return HealthOut(
        status="ok",
        version=request.app.version,
        dry_run=settings.dry_run,
        timezone=settings.timezone,
        active_assets=[plan.asset for plan in plans],
    )
