"""Servico de notificacoes via Telegram."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bot.models.incident import Incident, Severity

if TYPE_CHECKING:
    from telegram import Bot

    from bot.config import Config

logger = logging.getLogger(__name__)


class Notifier:
    """Envia notificacoes para canais do Telegram baseado na severidade."""

    def __init__(self, bot: Bot, config: Config):
        self.bot = bot
        self.config = config

    async def notify_new_incident(self, incident: Incident) -> None:
        """Notifica sobre novo incidente."""
        message = (
            f"\U0001f6a8 <b>NOVO INCIDENTE</b>\n\n"
            f"{incident.format_summary()}"
        )

        channels = self._get_channels(incident.severity)
        for channel_id in channels:
            await self._send(channel_id, message)

    async def notify_status_change(self, incident: Incident) -> None:
        """Notifica mudanca de status."""
        message = (
            f"\U0001f504 <b>STATUS ATUALIZADO</b>\n\n"
            f"{incident.format_summary()}"
        )

        if incident.channel_id:
            await self._send(incident.channel_id, message)

    async def notify_escalation(
        self, incident: Incident, level: int, assignee: str
    ) -> None:
        """Notifica escalonamento."""
        message = (
            f"\u26a0\ufe0f <b>ESCALONAMENTO - Nivel {level + 1}</b>\n\n"
            f"{incident.format_summary()}\n\n"
            f"\U0001f464 Escalonado para: <b>{assignee}</b>\n"
            f"\U0001f4ac Incidente sem ACK - acao imediata necessaria!"
        )

        channels = self._get_channels(incident.severity)
        for channel_id in channels:
            await self._send(channel_id, message)

    async def notify_resolved(self, incident: Incident) -> None:
        """Notifica resolucao."""
        message = (
            f"\u2705 <b>INCIDENTE RESOLVIDO</b>\n\n"
            f"{incident.format_summary()}"
        )

        channels = self._get_channels(incident.severity)
        for channel_id in channels:
            await self._send(channel_id, message)

    def _get_channels(self, severity: Severity) -> list[str]:
        """Determina canais de notificacao baseado na severidade."""
        channels = []

        if self.config.oncall_channel_id:
            channels.append(self.config.oncall_channel_id)

        if severity in (Severity.P1, Severity.P2) and self.config.alert_channel_id:
            channels.append(self.config.alert_channel_id)

        return channels

    async def _send(self, channel_id: str, message: str) -> None:
        """Envia mensagem para um canal."""
        try:
            await self.bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Erro ao enviar notificacao para %s", channel_id)
