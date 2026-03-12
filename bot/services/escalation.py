"""Logica de escalonamento automatico."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from bot.models.incident import Severity, Status

if TYPE_CHECKING:
    from bot.config import Config
    from bot.services.notifier import Notifier
    from bot.storage.database import Database

logger = logging.getLogger(__name__)


class EscalationService:
    """Gerencia escalonamento automatico de incidentes."""

    def __init__(self, config: Config, database: Database, notifier: Notifier):
        self.config = config
        self.db = database
        self.notifier = notifier
        self._task: asyncio.Task | None = None

    def get_timeout(self, severity: Severity) -> int:
        """Retorna timeout de escalonamento em segundos."""
        timeouts = {
            Severity.P1: self.config.escalation.P1,
            Severity.P2: self.config.escalation.P2,
            Severity.P3: self.config.escalation.P3,
            Severity.P4: self.config.escalation.P4,
        }
        return timeouts[severity]

    async def start(self) -> None:
        """Inicia loop de verificacao de escalonamento."""
        self._task = asyncio.create_task(self._check_loop())
        logger.info("Escalation service iniciado")

    async def stop(self) -> None:
        """Para o loop de escalonamento."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Escalation service parado")

    async def _check_loop(self) -> None:
        """Loop que verifica incidentes para escalonar."""
        while True:
            try:
                await self._check_escalations()
            except Exception:
                logger.exception("Erro ao verificar escalonamentos")
            await asyncio.sleep(30)

    async def _check_escalations(self) -> None:
        """Verifica e executa escalonamentos pendentes."""
        incidents = await self.db.get_unacknowledged_incidents()
        now = datetime.utcnow()

        for incident in incidents:
            if not incident.created_at:
                continue

            timeout = self.get_timeout(incident.severity)
            elapsed = (now - incident.created_at).total_seconds()

            expected_level = int(elapsed // timeout)
            if expected_level > incident.escalation_level:
                await self._escalate(incident, expected_level)

    async def _escalate(self, incident, new_level: int) -> None:
        """Executa escalonamento de um incidente."""
        schedule = await self.db.get_oncall_schedule()
        chain = schedule.get_escalation_chain()

        target = None
        if new_level < len(chain):
            target = chain[new_level]

        assignee = target.username if target else f"Nivel {new_level + 1}"

        await self.db.update_incident(
            incident.id,
            user="sistema",
            escalation_level=new_level,
            assignee=assignee,
        )

        await self.db.add_timeline_entry(
            incident.id,
            action=f"Escalonado para nivel {new_level + 1}",
            user="sistema",
            details=f"Sem ACK apos timeout. Novo responsavel: {assignee}",
        )

        updated = await self.db.get_incident(incident.id)
        if updated:
            await self.notifier.notify_escalation(updated, new_level, assignee)

        logger.warning(
            "INC-%04d escalonado para nivel %d -> %s",
            incident.id, new_level + 1, assignee,
        )
