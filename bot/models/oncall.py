"""Modelo de on-call."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OnCallEntry:
    """Entrada individual de on-call."""

    id: int = 0
    user_id: str = ""
    username: str = ""
    level: int = 1  # 1 = primario, 2 = secundario, 3 = gerente
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def level_label(self) -> str:
        labels = {1: "Primario", 2: "Secundario", 3: "Gerente"}
        return labels.get(self.level, f"Nivel {self.level}")


@dataclass
class OnCallSchedule:
    """Schedule completo de on-call."""

    entries: list[OnCallEntry] = field(default_factory=list)

    def get_current(self, level: int = 1) -> Optional[OnCallEntry]:
        """Retorna o on-call atual para o nivel especificado."""
        now = datetime.utcnow()
        for entry in self.entries:
            if entry.level != level:
                continue
            if entry.start_date and entry.end_date:
                if entry.start_date <= now <= entry.end_date:
                    return entry
            elif entry.start_date and entry.start_date <= now:
                return entry
        return None

    def get_escalation_chain(self) -> list[OnCallEntry]:
        """Retorna a cadeia de escalonamento ordenada por nivel."""
        now = datetime.utcnow()
        active = []
        for entry in self.entries:
            if entry.start_date and entry.end_date:
                if entry.start_date <= now <= entry.end_date:
                    active.append(entry)
            elif entry.start_date and entry.start_date <= now:
                active.append(entry)
        return sorted(active, key=lambda e: e.level)

    def format_schedule(self) -> str:
        """Formata schedule para Telegram."""
        if not self.entries:
            return "Nenhum on-call configurado."

        lines = ["\U0001f4c5 <b>On-Call Schedule</b>\n"]
        for entry in sorted(self.entries, key=lambda e: (e.start_date or datetime.min, e.level)):
            period = ""
            if entry.start_date and entry.end_date:
                period = f" ({entry.start_date:%d/%m} - {entry.end_date:%d/%m})"
            lines.append(
                f"  \U0001f464 <b>{entry.username}</b> - {entry.level_label}{period}"
            )
        return "\n".join(lines)
