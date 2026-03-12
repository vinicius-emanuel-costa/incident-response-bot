"""Camada de persistencia com SQLite (async)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from bot.models.incident import Incident, Severity, Status, TimelineEntry
from bot.models.oncall import OnCallEntry, OnCallSchedule
from bot.models.runbook import Runbook


class Database:
    """Gerencia conexao e operacoes no SQLite."""

    def __init__(self, db_path: str = "data/incidents.db"):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Cria o banco e as tabelas se nao existirem."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()

        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema)
            await db.commit()

    async def _get_db(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        return db

    # --- Incidents ---

    async def create_incident(self, incident: Incident) -> Incident:
        """Cria um novo incidente e retorna com ID preenchido."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """INSERT INTO incidents
                   (title, severity, status, assignee, created_by, created_at, channel_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    incident.title,
                    incident.severity.value,
                    incident.status.value,
                    incident.assignee,
                    incident.created_by,
                    incident.created_at or datetime.utcnow(),
                    incident.channel_id,
                ),
            )
            incident.id = cursor.lastrowid

            await db.execute(
                "INSERT INTO timeline (incident_id, action, user, details) VALUES (?, ?, ?, ?)",
                (incident.id, "Incidente criado", incident.created_by, incident.title),
            )
            await db.commit()
        return incident

    async def get_incident(self, incident_id: int) -> Optional[Incident]:
        """Busca incidente por ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM incidents WHERE id = ?", (incident_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            incident = self._row_to_incident(row)

            cursor = await db.execute(
                "SELECT * FROM timeline WHERE incident_id = ? ORDER BY timestamp",
                (incident_id,),
            )
            rows = await cursor.fetchall()
            incident.timeline = [
                TimelineEntry(
                    timestamp=datetime.fromisoformat(r["timestamp"]) if isinstance(r["timestamp"], str) else r["timestamp"],
                    action=r["action"],
                    user=r["user"],
                    details=r["details"] or "",
                )
                for r in rows
            ]
        return incident

    async def update_incident(
        self, incident_id: int, user: str, **fields
    ) -> Optional[Incident]:
        """Atualiza campos de um incidente."""
        allowed = {"status", "severity", "assignee", "acknowledged_at", "resolved_at", "escalation_level"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return await self.get_incident(incident_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = []
        for v in updates.values():
            if isinstance(v, (Severity, Status)):
                values.append(v.value)
            else:
                values.append(v)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                f"UPDATE incidents SET {set_clause} WHERE id = ?",
                (*values, incident_id),
            )

            action = ", ".join(f"{k}={v}" for k, v in fields.items())
            await db.execute(
                "INSERT INTO timeline (incident_id, action, user, details) VALUES (?, ?, ?, ?)",
                (incident_id, "Atualizado", user, action),
            )
            await db.commit()

        return await self.get_incident(incident_id)

    async def list_incidents(
        self, status: Optional[str] = None, severity: Optional[str] = None, limit: int = 20
    ) -> list[Incident]:
        """Lista incidentes com filtros opcionais."""
        query = "SELECT * FROM incidents WHERE 1=1"
        params: list = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_incident(r) for r in rows]

    async def get_open_incidents(self) -> list[Incident]:
        """Retorna incidentes que nao foram resolvidos."""
        return await self.list_incidents(status=None)

    async def get_unacknowledged_incidents(self) -> list[Incident]:
        """Retorna incidentes abertos sem ACK."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM incidents WHERE status = 'open' AND acknowledged_at IS NULL"
            )
            rows = await cursor.fetchall()
            return [self._row_to_incident(r) for r in rows]

    def _row_to_incident(self, row) -> Incident:
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return val

        return Incident(
            id=row["id"],
            title=row["title"],
            severity=Severity(row["severity"]),
            status=Status(row["status"]),
            assignee=row["assignee"] or "",
            created_by=row["created_by"] or "",
            created_at=parse_dt(row["created_at"]),
            acknowledged_at=parse_dt(row["acknowledged_at"]),
            resolved_at=parse_dt(row["resolved_at"]),
            escalation_level=row["escalation_level"] or 0,
            channel_id=row["channel_id"] or "",
        )

    # --- Timeline ---

    async def add_timeline_entry(
        self, incident_id: int, action: str, user: str, details: str = ""
    ) -> None:
        """Adiciona entrada na timeline."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO timeline (incident_id, action, user, details) VALUES (?, ?, ?, ?)",
                (incident_id, action, user, details),
            )
            await db.commit()

    # --- On-Call ---

    async def set_oncall(self, entry: OnCallEntry) -> OnCallEntry:
        """Define ou atualiza on-call."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """INSERT INTO oncall (user_id, username, level, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (entry.user_id, entry.username, entry.level, entry.start_date, entry.end_date),
            )
            entry.id = cursor.lastrowid
            await db.commit()
        return entry

    async def get_oncall_schedule(self) -> OnCallSchedule:
        """Retorna schedule completo de on-call."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM oncall ORDER BY level, start_date")
            rows = await cursor.fetchall()

            entries = [
                OnCallEntry(
                    id=r["id"],
                    user_id=r["user_id"],
                    username=r["username"],
                    level=r["level"],
                    start_date=datetime.fromisoformat(r["start_date"]) if r["start_date"] else None,
                    end_date=datetime.fromisoformat(r["end_date"]) if r["end_date"] else None,
                )
                for r in rows
            ]
        return OnCallSchedule(entries=entries)

    async def clear_oncall(self) -> None:
        """Limpa schedule de on-call."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM oncall")
            await db.commit()

    # --- Runbooks ---

    async def save_runbook(self, runbook: Runbook) -> None:
        """Salva ou atualiza runbook."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO runbooks (name, title, content, keywords)
                   VALUES (?, ?, ?, ?)""",
                (runbook.name, runbook.title, runbook.content, json.dumps(runbook.keywords)),
            )
            await db.commit()

    async def get_runbook(self, name: str) -> Optional[Runbook]:
        """Busca runbook por nome."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM runbooks WHERE name = ?", (name,))
            row = await cursor.fetchone()
            if not row:
                return None
            return Runbook(
                name=row["name"],
                title=row["title"],
                content=row["content"],
                keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            )

    async def list_runbooks(self) -> list[Runbook]:
        """Lista todos os runbooks."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM runbooks ORDER BY name")
            rows = await cursor.fetchall()
            return [
                Runbook(
                    name=r["name"],
                    title=r["title"],
                    content=r["content"],
                    keywords=json.loads(r["keywords"]) if r["keywords"] else [],
                )
                for r in rows
            ]

    async def find_runbooks(self, query: str) -> list[Runbook]:
        """Busca runbooks relevantes para uma query."""
        all_runbooks = await self.list_runbooks()
        return [rb for rb in all_runbooks if rb.matches(query)]

    # --- Metricas ---

    async def get_resolved_incidents(
        self, since: Optional[datetime] = None
    ) -> list[Incident]:
        """Retorna incidentes resolvidos para calculo de metricas."""
        query = "SELECT * FROM incidents WHERE status IN ('resolved', 'postmortem')"
        params: list = []

        if since:
            query += " AND resolved_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY resolved_at DESC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_incident(r) for r in rows]

    async def count_incidents_by_severity(
        self, since: Optional[datetime] = None
    ) -> dict[str, int]:
        """Conta incidentes por severidade."""
        query = "SELECT severity, COUNT(*) as cnt FROM incidents"
        params: list = []

        if since:
            query += " WHERE created_at >= ?"
            params.append(since.isoformat())

        query += " GROUP BY severity"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return {r["severity"]: r["cnt"] for r in rows}
