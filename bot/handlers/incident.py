"""Handlers de incidentes."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.models.incident import Incident, Severity, Status

if TYPE_CHECKING:
    from bot.services.notifier import Notifier
    from bot.services.timeline import TimelineService
    from bot.storage.database import Database

# Conversation states
TITLE, SEVERITY = range(2)


def get_user(update: Update) -> str:
    """Extrai username ou nome do usuario."""
    user = update.effective_user
    if not user:
        return "desconhecido"
    return user.username or user.first_name or str(user.id)


class IncidentHandlers:
    """Handlers para comandos de incidente."""

    def __init__(self, database: Database, notifier: Notifier, timeline: TimelineService):
        self.db = database
        self.notifier = notifier
        self.timeline = timeline

    def get_handlers(self) -> list:
        """Retorna lista de handlers para registrar no bot."""
        return [
            ConversationHandler(
                entry_points=[CommandHandler("create", self.create_start)],
                states={
                    TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_title)],
                    SEVERITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_severity)],
                },
                fallbacks=[CommandHandler("cancel", self.cancel)],
            ),
            CommandHandler("ack", self.acknowledge),
            CommandHandler("investigate", self.investigate),
            CommandHandler("resolve", self.resolve),
            CommandHandler("postmortem", self.postmortem),
            CommandHandler("status", self.status),
            CommandHandler("timeline", self.show_timeline),
            CommandHandler("list", self.list_incidents),
        ]

    async def create_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Inicia criacao de incidente."""
        args = context.args
        if args:
            # Modo rapido: /create P1 Titulo do incidente
            if args[0].upper() in ("P1", "P2", "P3", "P4"):
                severity = Severity(args[0].upper())
                title = " ".join(args[1:]) if len(args) > 1 else "Incidente sem titulo"
                return await self._create_incident(update, context, title, severity)

        await update.message.reply_text(
            "\U0001f6a8 <b>Criar Novo Incidente</b>\n\n"
            "Qual e o titulo do incidente?",
            parse_mode="HTML",
        )
        return TITLE

    async def create_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Recebe titulo do incidente."""
        context.user_data["incident_title"] = update.message.text
        await update.message.reply_text(
            "Qual a severidade?\n\n"
            "\U0001f534 <b>P1</b> - Critico (sistema fora do ar)\n"
            "\U0001f7e0 <b>P2</b> - Alto (funcionalidade impactada)\n"
            "\U0001f7e1 <b>P3</b> - Medio (degradacao)\n"
            "\U0001f535 <b>P4</b> - Baixo (inconveniencia)\n\n"
            "Responda com P1, P2, P3 ou P4:",
            parse_mode="HTML",
        )
        return SEVERITY

    async def create_severity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Recebe severidade e cria o incidente."""
        sev_text = update.message.text.upper().strip()
        if sev_text not in ("P1", "P2", "P3", "P4"):
            await update.message.reply_text(
                "Severidade invalida. Use P1, P2, P3 ou P4."
            )
            return SEVERITY

        title = context.user_data.get("incident_title", "Incidente sem titulo")
        severity = Severity(sev_text)
        return await self._create_incident(update, context, title, severity)

    async def _create_incident(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE,
        title: str, severity: Severity
    ) -> int:
        """Cria o incidente no banco e notifica."""
        user = get_user(update)
        channel_id = str(update.effective_chat.id) if update.effective_chat else ""

        # Busca on-call primario para atribuir
        schedule = await self.db.get_oncall_schedule()
        oncall = schedule.get_current(level=1)
        assignee = oncall.username if oncall else ""

        incident = Incident(
            title=title,
            severity=severity,
            status=Status.OPEN,
            assignee=assignee,
            created_by=user,
            channel_id=channel_id,
        )

        incident = await self.db.create_incident(incident)

        # Busca runbooks relevantes
        runbooks = await self.db.find_runbooks(title)
        runbook_msg = ""
        if runbooks:
            rb_names = ", ".join(f"<code>{rb.name}</code>" for rb in runbooks)
            runbook_msg = f"\n\n\U0001f4d6 Runbooks sugeridos: {rb_names}\nUse /runbook show <nome>"

        await update.message.reply_text(
            f"\u2705 Incidente criado!\n\n"
            f"{incident.format_summary()}{runbook_msg}",
            parse_mode="HTML",
        )

        await self.notifier.notify_new_incident(incident)

        return ConversationHandler.END

    async def acknowledge(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reconhece um incidente: /ack <id>"""
        if not context.args:
            await update.message.reply_text("Uso: /ack <id>")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        user = get_user(update)
        incident = await self.db.update_incident(
            inc_id, user,
            status=Status.ACKNOWLEDGED,
            acknowledged_at=datetime.utcnow(),
            assignee=user,
        )

        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await self.timeline.add_entry(inc_id, "Incidente reconhecido", user)
        await update.message.reply_text(
            f"\U0001f440 Incidente reconhecido!\n\n{incident.format_summary()}",
            parse_mode="HTML",
        )
        await self.notifier.notify_status_change(incident)

    async def investigate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Marca incidente como investigando: /investigate <id> [nota]"""
        if not context.args:
            await update.message.reply_text("Uso: /investigate <id> [nota]")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        user = get_user(update)
        note = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        incident = await self.db.update_incident(
            inc_id, user, status=Status.INVESTIGATING
        )

        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await self.timeline.add_entry(inc_id, "Investigacao iniciada", user, note)
        await update.message.reply_text(
            f"\U0001f50d Investigando!\n\n{incident.format_summary()}",
            parse_mode="HTML",
        )
        await self.notifier.notify_status_change(incident)

    async def resolve(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Resolve um incidente: /resolve <id> [nota]"""
        if not context.args:
            await update.message.reply_text("Uso: /resolve <id> [nota]")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        user = get_user(update)
        note = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        incident = await self.db.update_incident(
            inc_id, user,
            status=Status.RESOLVED,
            resolved_at=datetime.utcnow(),
        )

        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await self.timeline.add_entry(inc_id, "Incidente resolvido", user, note)
        await update.message.reply_text(
            f"\u2705 Incidente resolvido!\n\n{incident.format_summary()}",
            parse_mode="HTML",
        )
        await self.notifier.notify_resolved(incident)

    async def postmortem(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Marca incidente para postmortem: /postmortem <id> [nota]"""
        if not context.args:
            await update.message.reply_text("Uso: /postmortem <id> [nota]")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        user = get_user(update)
        note = " ".join(context.args[1:]) if len(context.args) > 1 else ""

        incident = await self.db.update_incident(
            inc_id, user, status=Status.POSTMORTEM
        )

        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await self.timeline.add_entry(inc_id, "Postmortem iniciado", user, note)
        await update.message.reply_text(
            f"\U0001f4dd Postmortem marcado!\n\n{incident.format_summary()}",
            parse_mode="HTML",
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra status de um incidente: /status <id>"""
        if not context.args:
            await update.message.reply_text("Uso: /status <id>")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        incident = await self.db.get_incident(inc_id)
        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await update.message.reply_text(
            incident.format_summary(), parse_mode="HTML"
        )

    async def show_timeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Mostra timeline de um incidente: /timeline <id>"""
        if not context.args:
            await update.message.reply_text("Uso: /timeline <id>")
            return

        try:
            inc_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("ID invalido.")
            return

        incident = await self.db.get_incident(inc_id)
        if not incident:
            await update.message.reply_text(f"Incidente INC-{inc_id:04d} nao encontrado.")
            return

        await update.message.reply_text(
            incident.format_timeline(), parse_mode="HTML"
        )

    async def list_incidents(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Lista incidentes: /list [open|resolved|all]"""
        filter_status = None
        if context.args:
            arg = context.args[0].lower()
            if arg == "open":
                filter_status = "open"
            elif arg == "resolved":
                filter_status = "resolved"

        incidents = await self.db.list_incidents(status=filter_status, limit=10)

        if not incidents:
            await update.message.reply_text("Nenhum incidente encontrado.")
            return

        lines = ["\U0001f4cb <b>Incidentes</b>\n"]
        for inc in incidents:
            lines.append(
                f"  {inc.severity.emoji} <b>INC-{inc.id:04d}</b> "
                f"{inc.status.emoji} {inc.title[:40]}"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancela criacao de incidente."""
        await update.message.reply_text("Criacao de incidente cancelada.")
        return ConversationHandler.END
