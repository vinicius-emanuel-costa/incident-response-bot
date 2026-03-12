"""Handlers de metricas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

if TYPE_CHECKING:
    from bot.services.metrics import MetricsService


class MetricsHandlers:
    """Handlers para comandos de metricas."""

    def __init__(self, metrics_service: MetricsService):
        self.metrics = metrics_service

    def get_handlers(self) -> list:
        """Retorna lista de handlers para registrar no bot."""
        return [
            CommandHandler("metrics", self.show_metrics),
            CommandHandler("mttr", self.show_mttr),
        ]

    async def show_metrics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra relatorio de metricas: /metrics [dias]"""
        days = 30
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                pass

        report = await self.metrics.format_report(days)
        await update.message.reply_text(report, parse_mode="HTML")

    async def show_mttr(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra MTTR e MTTA: /mttr [dias]"""
        days = 30
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                pass

        report = await self.metrics.format_report(days)
        await update.message.reply_text(report, parse_mode="HTML")
