from psycopg_pool import ConnectionPool
from contextlib import contextmanager
from .config import settings

# Ponytail: lazy pool; one pool per process. psycopg3 native.
pool = ConnectionPool(
    conninfo=(
        f"host={settings.db_host} port={settings.db_port} dbname={settings.db_name} "
        f"user={settings.db_user} password={settings.db_password}"
    ),
    min_size=1,
    max_size=5,
    open=True,
)


@contextmanager
def get_conn():
    with pool.connection() as conn:
        yield conn
