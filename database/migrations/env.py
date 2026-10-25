
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

# --------------------------------------------------
# 1. Locate the main project directory
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT))

# --------------------------------------------------
# 2. Load PostgreSQL credentials from .env
# --------------------------------------------------

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)

# --------------------------------------------------
# 3. Construct PostgreSQL connection URL safely
# --------------------------------------------------

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host="localhost",
    port=5432,
    database=os.environ["POSTGRES_DB"],
)

DATABASE_URL = database_url.render_as_string(
    hide_password=False
)

# Set DATABASE_URL before importing database.db
os.environ["DATABASE_URL"] = DATABASE_URL

# --------------------------------------------------
# 4. Import SQLAlchemy models
# --------------------------------------------------

from database.db import Base
import database.models

# --------------------------------------------------
# 5. Configure Alembic
# --------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Escape percent signs for ConfigParser
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%")
)

# --------------------------------------------------
# 6. Offline migration configuration
# --------------------------------------------------

def run_migrations_offline():
    """
    Run migrations without a live database connection.
    """

    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------
# 7. Online migration configuration
# --------------------------------------------------

def run_migrations_online():
    """
    Run migrations using a PostgreSQL connection.
    """

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 5},
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# --------------------------------------------------
# 8. Execute migration
# --------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
