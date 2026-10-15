import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

url = os.environ.get("DATABASE_URL")
if not url:
    raise RuntimeError("DATABASE_URL obrigatório para migrações")
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
