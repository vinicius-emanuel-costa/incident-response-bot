"""Ponto de entrada do Incident Response Bot."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config
from bot.handlers.incident import IncidentHandlers
from bot.handlers.metrics import MetricsHandlers
from bot.handlers.oncall import OnCallHandlers
from bot.handlers.runbook import RunbookHandlers
from bot.models.runbook import Runbook
from bot.services.escalation import EscalationService
from bot.services.metrics import MetricsService
from bot.services.notifier import Notifier
from bot.services.timeline import TimelineService
from bot.storage.database import Database

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /start."""
    await update.message.reply_text(
        "\U0001f6a8 <b>Incident Response Bot</b>\n\n"
        "Bot para gestao de incidentes com escalonamento automatico, "
        "runbooks e metricas.\n\n"
        "<b>Comandos principais:</b>\n"
        "  /create [P1-P4] [titulo] - Criar incidente\n"
        "  /ack <id> - Reconhecer incidente\n"
        "  /investigate <id> - Investigar\n"
        "  /resolve <id> - Resolver\n"
        "  /status <id> - Ver status\n"
        "  /timeline <id> - Ver timeline\n"
        "  /list [open|resolved] - Listar incidentes\n"
        "  /runbook list|show <nome> - Runbooks\n"
        "  /oncall show|set|rotate - On-call\n"
        "  /metrics [dias] - Metricas\n"
        "  /help - Ajuda completa",
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler do comando /help."""
    await update.message.reply_text(
        "\U0001f4d6 <b>Ajuda - Incident Response Bot</b>\n\n"
        "<b>Incidentes:</b>\n"
        "  /create - Criar incidente (interativo)\n"
        "  /create P1 API fora do ar - Criar rapido\n"
        "  /ack 1 - Reconhecer INC-0001\n"
        "  /investigate 1 Verificando logs - Investigar\n"
        "  /resolve 1 Corrigido deploy - Resolver\n"
        "  /postmortem 1 - Marcar postmortem\n"
        "  /status 1 - Ver status\n"
        "  /timeline 1 - Ver timeline\n"
        "  /list - Listar incidentes\n\n"
        "<b>Runbooks:</b>\n"
        "  /runbook list - Listar runbooks\n"
        "  /runbook show high-cpu - Ver runbook\n\n"
        "<b>On-Call:</b>\n"
        "  /oncall show - Ver schedule\n"
        "  /oncall set 1 @joao 7 - Definir on-call\n"
        "  /oncall rotate - Rotacionar\n\n"
        "<b>Metricas:</b>\n"
        "  /metrics - Relatorio 30 dias\n"
        "  /metrics 7 - Relatorio 7 dias\n"
        "  /mttr - MTTR e MTTA\n\n"
        "<b>Severidades:</b>\n"
        "  P1 \U0001f534 Critico - Escalonamento em 5min\n"
        "  P2 \U0001f7e0 Alto - Escalonamento em 15min\n"
        "  P3 \U0001f7e1 Medio - Escalonamento em 30min\n"
        "  P4 \U0001f535 Baixo - Escalonamento em 60min",
        parse_mode="HTML",
    )


async def load_runbooks(database: Database) -> None:
    """Carrega runbooks dos arquivos markdown."""
    runbooks_dir = Path(__file__).parent.parent / "runbooks"
    if not runbooks_dir.exists():
        logger.warning("Diretorio de runbooks nao encontrado: %s", runbooks_dir)
        return

    # Mapeamento de runbooks para keywords
    runbook_meta = {
        "high-cpu": {
            "title": "High CPU Usage",
            "keywords": ["cpu", "alta", "load", "processamento", "lento"],
        },
        "disk-full": {
            "title": "Disk Full",
            "keywords": ["disco", "disk", "cheio", "full", "espaco", "storage"],
        },
        "service-down": {
            "title": "Service Down",
            "keywords": ["fora", "down", "indisponivel", "unreachable", "timeout", "servico"],
        },
        "database-slow": {
            "title": "Database Slow Queries",
            "keywords": ["database", "banco", "lento", "query", "slow", "db"],
        },
        "certificate-expiring": {
            "title": "SSL Certificate Expiring",
            "keywords": ["certificado", "ssl", "tls", "expirando", "certificate", "https"],
        },
    }

    for md_file in runbooks_dir.glob("*.md"):
        name = md_file.stem
        content = md_file.read_text()
        meta = runbook_meta.get(name, {"title": name, "keywords": []})

        runbook = Runbook(
            name=name,
            title=meta["title"],
            content=content,
            keywords=meta["keywords"],
        )
        await database.save_runbook(runbook)
        logger.info("Runbook carregado: %s", name)


async def post_init(application: Application) -> None:
    """Callback pos-inicializacao: configura banco, servicos e handlers."""
    config = application.bot_data["config"]
    database = Database(config.database_path)
    await database.initialize()

    application.bot_data["database"] = database

    # Carrega runbooks
    await load_runbooks(database)

    # Servicos
    notifier = Notifier(application.bot, config)
    timeline_service = TimelineService(database)
    metrics_service = MetricsService(database)
    escalation_service = EscalationService(config, database, notifier)

    application.bot_data["notifier"] = notifier
    application.bot_data["escalation"] = escalation_service

    # Inicia escalonamento automatico
    await escalation_service.start()

    # Registra handlers
    incident_handlers = IncidentHandlers(database, notifier, timeline_service)
    runbook_handlers = RunbookHandlers(database)
    oncall_handlers = OnCallHandlers(database)
    metrics_handlers = MetricsHandlers(metrics_service)

    for handler in incident_handlers.get_handlers():
        application.add_handler(handler)
    for handler in runbook_handlers.get_handlers():
        application.add_handler(handler)
    for handler in oncall_handlers.get_handlers():
        application.add_handler(handler)
    for handler in metrics_handlers.get_handlers():
        application.add_handler(handler)

    # Comandos basicos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Define menu de comandos do bot
    commands = [
        BotCommand("start", "Iniciar bot"),
        BotCommand("create", "Criar incidente"),
        BotCommand("ack", "Reconhecer incidente"),
        BotCommand("investigate", "Investigar incidente"),
        BotCommand("resolve", "Resolver incidente"),
        BotCommand("status", "Ver status do incidente"),
        BotCommand("timeline", "Ver timeline do incidente"),
        BotCommand("list", "Listar incidentes"),
        BotCommand("runbook", "Ver runbooks"),
        BotCommand("oncall", "Gerenciar on-call"),
        BotCommand("metrics", "Ver metricas"),
        BotCommand("help", "Ajuda"),
    ]
    await application.bot.set_my_commands(commands)

    logger.info("Bot inicializado com sucesso!")


async def post_shutdown(application: Application) -> None:
    """Callback de shutdown: para servicos."""
    escalation = application.bot_data.get("escalation")
    if escalation:
        await escalation.stop()
    logger.info("Bot encerrado.")


def main() -> None:
    """Funcao principal."""
    config = Config.from_env()
    config.validate()

    application = (
        Application.builder()
        .token(config.telegram_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["config"] = config

    logger.info("Iniciando Incident Response Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
