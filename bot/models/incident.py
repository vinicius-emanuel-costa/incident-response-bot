"""Modelo de incidente."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    P1 = "P1"  # Critico
    P2 = "P2"  # Alto
    P3 = "P3"  # Medio
    P4 = "P4"  # Baixo

    @property
    def label(self) -> str:
        labels = {
            "P1": "Critico",
            "P2": "Alto",
            "P3": "Medio",
            "P4": "Baixo",
        }
        return labels[self.value]

    @property
    def emoji(self) -> str:
        emojis = {
            "P1": "\U0001f534",  # red circle
            "P2": "\U0001f7e0",  # orange circle
            "P3": "\U0001f7e1",  # yellow circle
            "P4": "\U0001f535",  # blue circle
        }
        return emojis[self.value]


class Status(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    POSTMORTEM = "postmortem"

    @property
    def label(self) -> str:
        labels = {
            "open": "Aberto",
            "acknowledged": "Reconhecido",
            "investigating": "Investigando",
            "resolved": "Resolvido",
            "postmortem": "Postmortem",
        }
        return labels[self.value]

    @property
    def emoji(self) -> str:
        emojis = {
            "open": "\U0001f6a8",          # rotating light
            "acknowledged": "\U0001f440",   # eyes
            "investigating": "\U0001f50d",  # magnifying glass
            "resolved": "\u2705",           # check mark
            "postmortem": "\U0001f4dd",     # memo
        }
        return emojis[self.value]


@dataclass
class TimelineEntry:
    """Entrada na timeline do incidente."""

    timestamp: datetime
    action: str
    user: str
    details: str = ""


@dataclass
class Incident:
    """Modelo principal de incidente."""

    id: int = 0
    title: str = ""
    severity: Severity = Severity.P4
    status: Status = Status.OPEN
    assignee: str = ""
    created_by: str = ""
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    timeline: list[TimelineEntry] = field(default_factory=list)
    escalation_level: int = 0
    channel_id: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def format_summary(self) -> str:
        """Formata resumo do incidente para Telegram."""
        duration = ""
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            minutes = int(delta.total_seconds() / 60)
            duration = f"\n\u23f1 Duracao: {minutes} min"

        ack_time = ""
        if self.acknowledged_at and self.created_at:
            delta = self.acknowledged_at - self.created_at
            seconds = int(delta.total_seconds())
            ack_time = f"\n\u23f0 Tempo ate ACK: {seconds}s"

        return (
            f"{self.severity.emoji} <b>INC-{self.id:04d}</b> | "
            f"{self.severity.value} - {self.severity.label}\n"
            f"{self.status.emoji} Status: {self.status.label}\n\n"
            f"\U0001f4cc <b>{self.title}</b>\n"
            f"\U0001f464 Responsavel: {self.assignee or 'Nao atribuido'}\n"
            f"\U0001f4c5 Criado: {self.created_at:%Y-%m-%d %H:%M:%S UTC}"
            f"{ack_time}{duration}"
        )

    def format_timeline(self) -> str:
        """Formata timeline completa."""
        if not self.timeline:
            return "Nenhum evento registrado."

        lines = [f"\U0001f4dc <b>Timeline INC-{self.id:04d}</b>\n"]
        for entry in self.timeline:
            detail = f" - {entry.details}" if entry.details else ""
            lines.append(
                f"  <code>{entry.timestamp:%H:%M:%S}</code> "
                f"[{entry.user}] {entry.action}{detail}"
            )
        return "\n".join(lines)
