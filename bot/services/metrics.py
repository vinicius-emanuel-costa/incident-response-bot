"""Servico de metricas de incidentes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from bot.models.incident import Incident, Severity

if TYPE_CHECKING:
    from bot.storage.database import Database


class MetricsService:
    """Calcula metricas de incidentes (MTTR, MTTA, contagem)."""

    def __init__(self, database: Database):
        self.db = database

    async def calculate_mttr(
        self, since: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Calcula Mean Time To Resolve (em minutos).
        Considera apenas incidentes resolvidos.
        """
        incidents = await self.db.get_resolved_incidents(since)
        if not incidents:
            return None

        total_seconds = 0.0
        count = 0
        for inc in incidents:
            if inc.created_at and inc.resolved_at:
                delta = (inc.resolved_at - inc.created_at).total_seconds()
                total_seconds += delta
                count += 1

        if count == 0:
            return None
        return (total_seconds / count) / 60.0

    async def calculate_mtta(
        self, since: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Calcula Mean Time To Acknowledge (em minutos).
        Considera apenas incidentes que foram reconhecidos.
        """
        incidents = await self.db.get_resolved_incidents(since)
        if not incidents:
            return None

        total_seconds = 0.0
        count = 0
        for inc in incidents:
            if inc.created_at and inc.acknowledged_at:
                delta = (inc.acknowledged_at - inc.created_at).total_seconds()
                total_seconds += delta
                count += 1

        if count == 0:
            return None
        return (total_seconds / count) / 60.0

    async def get_incident_counts(
        self, since: Optional[datetime] = None
    ) -> dict[str, int]:
        """Retorna contagem de incidentes por severidade."""
        return await self.db.count_incidents_by_severity(since)

    async def format_report(self, days: int = 30) -> str:
        """Gera relatorio formatado de metricas."""
        since = datetime.utcnow() - timedelta(days=days)

        mttr = await self.calculate_mttr(since)
        mtta = await self.calculate_mtta(since)
        counts = await self.get_incident_counts(since)
        total = sum(counts.values())

        lines = [
            f"\U0001f4ca <b>Metricas de Incidentes</b> (ultimos {days} dias)\n",
            f"\U0001f4c8 Total de incidentes: <b>{total}</b>",
        ]

        for sev in ["P1", "P2", "P3", "P4"]:
            emoji = Severity(sev).emoji
            count = counts.get(sev, 0)
            lines.append(f"  {emoji} {sev}: {count}")

        lines.append("")

        if mttr is not None:
            if mttr >= 60:
                mttr_str = f"{mttr / 60:.1f}h"
            else:
                mttr_str = f"{mttr:.0f}min"
            lines.append(f"\u23f1 MTTR: <b>{mttr_str}</b>")
        else:
            lines.append("\u23f1 MTTR: <i>sem dados</i>")

        if mtta is not None:
            if mtta >= 60:
                mtta_str = f"{mtta / 60:.1f}h"
            else:
                mtta_str = f"{mtta:.0f}min"
            lines.append(f"\u23f0 MTTA: <b>{mtta_str}</b>")
        else:
            lines.append("\u23f0 MTTA: <i>sem dados</i>")

        return "\n".join(lines)
