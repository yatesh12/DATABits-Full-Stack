from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware, Request, Response
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from core.config import get_settings
from core.database import engine

logger = logging.getLogger(__name__)

settings = get_settings()


def _get_alembic_config() -> AlembicConfig:
    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", str(Path("alembic").resolve()))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_SYNC_URL)
    return alembic_cfg


def run_migrations() -> None:
    from alembic import command

    alembic_cfg = _get_alembic_config()
    logger.info("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations complete.")


def run_migrations_downgrade(revision: str = "-1") -> None:
    from alembic import command

    alembic_cfg = _get_alembic_config()
    logger.warning("Reverting migration to: %s", revision)
    command.downgrade(alembic_cfg, revision)


def check_migrations() -> dict[str, bool | str]:
    try:
        alembic_cfg = _get_alembic_config()
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        if head is None:
            return {"up_to_date": False, "current": None, "head": None}
        return {"up_to_date": True, "current": head, "head": head}
    except Exception as e:
        return {"up_to_date": False, "error": str(e)}


async def get_current_revision() -> Optional[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT version_num FROM alembic_version")
        )
        row = result.fetchone()
        if row:
            return row[0]
        return None


def migration_needed() -> bool:
    try:
        alembic_cfg = _get_alembic_config()
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        return head is not None
    except Exception:
        return True


class AutoMigrationMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: StarletteResponse,
        run_on_startup: bool = True,
    ) -> None:
        super().__init__(app)
        self.run_on_startup = run_on_startup
        self._migrations_run = False

    async def dispatch(
        self,
        request: StarletteRequest,
        call_next: Request,
    ) -> Response:
        if self.run_on_startup and not self._migrations_run:
            try:
                run_migrations()
                self._migrations_run = True
            except Exception as e:
                logger.error("Auto migration failed: %s", e)

        return await call_next(request)
