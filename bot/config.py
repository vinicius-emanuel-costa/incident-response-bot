"""Configuracao do bot via variaveis de ambiente."""

import os
from dataclasses import dataclass, field


@dataclass
class EscalationConfig:
    """Timeouts de escalonamento por severidade (em segundos)."""

    P1: int = 300      # 5 minutos
    P2: int = 900      # 15 minutos
    P3: int = 1800     # 30 minutos
    P4: int = 3600     # 60 minutos


@dataclass
class Config:
    """Configuracao central do bot."""

    telegram_token: str = ""
    oncall_channel_id: str = ""
    alert_channel_id: str = ""
    database_path: str = "data/incidents.db"
    escalation: EscalationConfig = field(default_factory=EscalationConfig)
    timezone: str = "America/Sao_Paulo"

    @classmethod
    def from_env(cls) -> "Config":
        """Carrega configuracao a partir de variaveis de ambiente."""
        return cls(
            telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
            oncall_channel_id=os.getenv("ONCALL_CHANNEL_ID", ""),
            alert_channel_id=os.getenv("ALERT_CHANNEL_ID", ""),
            database_path=os.getenv("DATABASE_PATH", "data/incidents.db"),
            escalation=EscalationConfig(
                P1=int(os.getenv("ESCALATION_P1", "300")),
                P2=int(os.getenv("ESCALATION_P2", "900")),
                P3=int(os.getenv("ESCALATION_P3", "1800")),
                P4=int(os.getenv("ESCALATION_P4", "3600")),
            ),
            timezone=os.getenv("TIMEZONE", "America/Sao_Paulo"),
        )

    def validate(self) -> None:
        """Valida campos obrigatorios."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN e obrigatorio")
