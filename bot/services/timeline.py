"""Servico de timeline de incidentes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bot.models.incident import TimelineEntry

if TYPE_CHECKING:
    from bot.storage.database import Database


class TimelineService:
    """Gerencia timeline de incidentes."""

    def __init__(self, database: Database):
        self.db = database

    async def add_entry(
        self,
        incident_id: int,
        action: str,
        user: str,
        details: str = "",
    ) -> TimelineEntry:
        """Adiciona entrada na timeline com timestamp."""
        await self.db.add_timeline_entry(incident_id, action, user, details)
        return TimelineEntry(
            timestamp=datetime.utcnow(),
            action=action,
            user=user,
            details=details,
        )

    async def get_timeline(self, incident_id: int) -> list[TimelineEntry]:
        """Retorna timeline completa de um incidente."""
        incident = await self.db.get_incident(incident_id)
        if not incident:
            return []
        return incident.timeline
