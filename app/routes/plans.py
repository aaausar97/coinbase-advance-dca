"""Configured DCA plans endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.plan import PlanListOut, PlanOut


router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=PlanListOut)
async def list_plans(request: Request) -> PlanListOut:
    settings = request.app.state.settings
    plans = getattr(request.app.state, "plans", []) or []
    scheduler = getattr(request.app.state, "scheduler", None)

    items = [
        PlanOut(
            asset=plan.asset,
            product_id=plan.product_id,
            amount=plan.amount,
            cron=plan.cron,
            next_run_at=scheduler.next_run_for(plan.asset) if scheduler else None,
        )
        for plan in plans
    ]

    return PlanListOut(plans=items, count=len(items), dry_run=settings.dry_run)
