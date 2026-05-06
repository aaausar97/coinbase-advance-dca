"""Aggregate API router."""

from fastapi import APIRouter

from app.routes import balances, buys, health, history, plans


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(plans.router)
api_router.include_router(buys.router)
api_router.include_router(history.router)
api_router.include_router(balances.router)


__all__ = ["api_router"]
