"""APScheduler wrapper for recurring DCA buys."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Settings
from app.modules.coinbase import CoinbaseClient
from app.modules.dca import DCAService
from app.utils.parsers import Plan


logger = logging.getLogger(__name__)


class SchedulerService:
    """Owns the AsyncIOScheduler and registers one job per active DCA plan."""

    def __init__(self, settings: Settings, client: CoinbaseClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self._scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self._plans: list[Plan] = []

    async def _run_job(self, asset: str) -> None:
        """Wrapper invoked by APScheduler. Looks up the live plan amount each run."""

        try:
            await DCAService.execute_buy(
                asset=asset,
                client=self._client,
                settings=self._settings,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Scheduled buy failed for %s", asset)

    def register_jobs(self, plans: Iterable[Plan]) -> None:
        self._plans = list(plans)
        for plan in self._plans:
            self._scheduler.add_job(
                self._run_job,
                trigger=CronTrigger.from_crontab(plan.cron, timezone=self._settings.timezone),
                args=[plan.asset],
                id=f"dca-{plan.asset}",
                name=f"DCA {plan.asset} ${plan.amount}",
                replace_existing=True,
                misfire_grace_time=300,
                coalesce=True,
                max_instances=1,
            )
            logger.info(
                "Registered cron job: dca-%s amount=$%s cron='%s'",
                plan.asset,
                plan.amount,
                plan.cron,
            )

    @property
    def plans(self) -> list[Plan]:
        return list(self._plans)

    def next_run_for(self, asset: str) -> datetime | None:
        job = self._scheduler.get_job(f"dca-{asset.upper()}")
        return job.next_run_time if job else None

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
