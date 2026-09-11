"""psycopg3 async connection pool — lazy init to avoid event-loop-in-constructor error."""
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
from .config import settings

_pool: AsyncConnectionPool | None = None


def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=(
                f"host={settings.db_host} port={settings.db_port} "
                f"dbname={settings.db_name} user={settings.db_user} password={settings.db_password}"
            ),
            min_size=1,
            max_size=5,
        )
    return _pool


@asynccontextmanager
async def get_conn():
    pool = _get_pool()
    async with pool.connection() as conn:
        yield conn
