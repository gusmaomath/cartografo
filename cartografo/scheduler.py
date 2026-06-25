"""Agendamento com APScheduler."""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import CRON_DIA_SEMANA, CRON_HORA
from .pipeline import executar_ciclo_completo

log = logging.getLogger("cartografo.scheduler")


def iniciar_agendador() -> None:
    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(
        executar_ciclo_completo,
        CronTrigger(day_of_week=CRON_DIA_SEMANA, hour=CRON_HORA, minute=0),
        id="ciclo_cartografo", replace_existing=True,
    )
    log.info("Agendador iniciado: %s às %dh.", CRON_DIA_SEMANA, CRON_HORA)
    scheduler.start()
