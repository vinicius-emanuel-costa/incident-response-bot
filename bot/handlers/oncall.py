"""Handlers de on-call."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.models.oncall import OnCallEntry

if TYPE_CHECKING:
    from bot.storage.database import Database


def get_user(update: Update) -> tuple[str, str]:
    """Retorna (user_id, username)."""
    user = update.effective_user
    if not user:
        return ("0", "desconhecido")
    return (str(user.id), user.username or user.first_name or str(user.id))


class OnCallHandlers:
    """Handlers para comandos de on-call."""

    def __init__(self, database: Database):
        self.db = database

    def get_handlers(self) -> list:
        """Retorna lista de handlers para registrar no bot."""
        return [
            CommandHandler("oncall", self.oncall),
        ]

    async def oncall(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando principal de on-call: /oncall show | set | rotate"""
        if not context.args:
            await self._show_schedule(update)
            return

        subcommand = context.args[0].lower()

        if subcommand == "show":
            await self._show_schedule(update)
        elif subcommand == "set":
            await self._set_oncall(update, context)
        elif subcommand == "rotate":
            await self._rotate(update, context)
        elif subcommand == "clear":
            await self._clear(update)
        else:
            await update.message.reply_text(
                "\U0001f4c5 <b>On-Call</b>\n\n"
                "Uso:\n"
                "  /oncall show - Mostra schedule atual\n"
                "  /oncall set <nivel> <@usuario> <dias> - Define on-call\n"
                "  /oncall rotate - Rotaciona on-call primario\n"
                "  /oncall clear - Limpa schedule",
                parse_mode="HTML",
            )

    async def _show_schedule(self, update: Update) -> None:
        """Mostra schedule de on-call."""
        schedule = await self.db.get_oncall_schedule()
        await update.message.reply_text(
            schedule.format_schedule(), parse_mode="HTML"
        )

    async def _set_oncall(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Define on-call: /oncall set <nivel> <username> <dias>"""
        if len(context.args) < 4:
            await update.message.reply_text(
                "Uso: /oncall set <nivel> <username> <dias>\n"
                "Exemplo: /oncall set 1 @joao 7"
            )
            return

        try:
            level = int(context.args[1])
            username = context.args[2].lstrip("@")
            days = int(context.args[3])
        except (ValueError, IndexError):
            await update.message.reply_text("Parametros invalidos.")
            return

        now = datetime.utcnow()
        entry = OnCallEntry(
            user_id="0",
            username=username,
            level=level,
            start_date=now,
            end_date=now + timedelta(days=days),
        )

        await self.db.set_oncall(entry)
        await update.message.reply_text(
            f"\u2705 On-call configurado!\n\n"
            f"\U0001f464 {username} - {entry.level_label}\n"
            f"\U0001f4c5 {now:%d/%m/%Y} a {entry.end_date:%d/%m/%Y}",
            parse_mode="HTML",
        )

    async def _rotate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Rotaciona on-call: promove secundario para primario."""
        schedule = await self.db.get_oncall_schedule()
        chain = schedule.get_escalation_chain()

        if len(chain) < 2:
            await update.message.reply_text(
                "Precisa de pelo menos 2 niveis configurados para rotacionar."
            )
            return

        # Limpa schedule atual e recria com rotacao
        await self.db.clear_oncall()

        now = datetime.utcnow()
        new_entries = []

        # Secundario vira primario
        new_primary = OnCallEntry(
            user_id=chain[1].user_id,
            username=chain[1].username,
            level=1,
            start_date=now,
            end_date=now + timedelta(days=7),
        )
        new_entries.append(new_primary)

        # Primario vira secundario
        new_secondary = OnCallEntry(
            user_id=chain[0].user_id,
            username=chain[0].username,
            level=2,
            start_date=now,
            end_date=now + timedelta(days=7),
        )
        new_entries.append(new_secondary)

        # Mantem outros niveis
        for entry in chain[2:]:
            entry.start_date = now
            entry.end_date = now + timedelta(days=7)
            new_entries.append(entry)

        for entry in new_entries:
            await self.db.set_oncall(entry)

        await update.message.reply_text(
            f"\U0001f504 On-call rotacionado!\n\n"
            f"\U0001f464 Primario: <b>{new_primary.username}</b>\n"
            f"\U0001f464 Secundario: <b>{new_secondary.username}</b>",
            parse_mode="HTML",
        )

    async def _clear(self, update: Update) -> None:
        """Limpa schedule de on-call."""
        await self.db.clear_oncall()
        await update.message.reply_text("\U0001f5d1 Schedule de on-call limpo.")
