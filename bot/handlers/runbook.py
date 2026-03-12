"""Handlers de runbooks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

if TYPE_CHECKING:
    from bot.storage.database import Database


class RunbookHandlers:
    """Handlers para comandos de runbook."""

    def __init__(self, database: Database):
        self.db = database

    def get_handlers(self) -> list:
        """Retorna lista de handlers para registrar no bot."""
        return [
            CommandHandler("runbook", self.runbook),
            CommandHandler("runbooks", self.list_runbooks),
        ]

    async def runbook(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando principal de runbook: /runbook show <nome> | /runbook list"""
        if not context.args:
            await update.message.reply_text(
                "\U0001f4d6 <b>Runbooks</b>\n\n"
                "Uso:\n"
                "  /runbook list - Lista todos os runbooks\n"
                "  /runbook show <nome> - Mostra um runbook\n"
                "  /runbooks - Atalho para listar",
                parse_mode="HTML",
            )
            return

        subcommand = context.args[0].lower()

        if subcommand == "list":
            await self.list_runbooks(update, context)
        elif subcommand == "show":
            if len(context.args) < 2:
                await update.message.reply_text("Uso: /runbook show <nome>")
                return
            name = context.args[1]
            await self._show_runbook(update, name)
        else:
            # Tenta interpretar como nome do runbook
            await self._show_runbook(update, subcommand)

    async def list_runbooks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Lista todos os runbooks disponiveis."""
        runbooks = await self.db.list_runbooks()

        if not runbooks:
            await update.message.reply_text("Nenhum runbook cadastrado.")
            return

        lines = ["\U0001f4d6 <b>Runbooks Disponiveis</b>\n"]
        for rb in runbooks:
            kw = ", ".join(rb.keywords[:3]) if rb.keywords else ""
            lines.append(f"  \U0001f4d7 <code>{rb.name}</code> - {rb.title}")
            if kw:
                lines.append(f"      Tags: <i>{kw}</i>")

        lines.append("\n\U0001f449 Use /runbook show <nome> para ver detalhes")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def _show_runbook(self, update: Update, name: str) -> None:
        """Mostra um runbook especifico."""
        runbook = await self.db.get_runbook(name)

        if not runbook:
            await update.message.reply_text(
                f"Runbook '{name}' nao encontrado.\n"
                f"Use /runbook list para ver os disponiveis."
            )
            return

        await update.message.reply_text(
            runbook.format_message(), parse_mode="HTML"
        )
