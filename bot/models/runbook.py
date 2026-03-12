"""Modelo de runbook."""

from dataclasses import dataclass


@dataclass
class Runbook:
    """Runbook de resposta a incidentes."""

    name: str
    title: str
    content: str
    keywords: list[str]

    def format_message(self) -> str:
        """Formata runbook para Telegram."""
        return (
            f"\U0001f4d6 <b>Runbook: {self.title}</b>\n"
            f"\U0001f3f7 <code>{self.name}</code>\n\n"
            f"{self.content}"
        )

    def matches(self, query: str) -> bool:
        """Verifica se o runbook e relevante para a query."""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.keywords)
