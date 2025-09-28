# -*- coding: utf-8 -*-
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import our models and configuration
from app.core.config import settings
from app.core.database import Base

# Import all models to ensure they're registered with SQLAlchemy
from app.models.user import User
from app.models.template import PDFTemplate, TemplateVersion
from app.models.comparison import Comparison, ComparisonField

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Modificación en la función run_migrations_online()

def run_migrations_online() -> None:
    # 1. Definir los parámetros de conexión directamente
    # Usa un diccionario para pasar los componentes (¡asegúrate que la password sea ASCII limpia!)
    connection_params = {
        "host": "localhost",
        "port": "5432",
        "username": "sepe_user",
        "password": "sepe_password", # REEMPLAZA por tu password limpia REAL
        "database": "sepe_comparator"
    }

    # 2. Configurar el URL directamente en la configuración de Alembic
    # Usaremos una sintaxis de URL que SQLAlchemy pueda entender 
    url = "postgresql://{username}:{password}@{host}:{port}/{database}".format(**connection_params)
    
    # Establecer la URL limpia en el objeto config
    config.set_main_option("sqlalchemy.url", url)

    # 3. CREAR LA TRAZABILIDAD AQUÍ 💡
    print("--- DEBUG: URL como cadena (repr) ---")
    print(repr(url))
    print("--- DEBUG: URL como bytes (UTF-8) ---")
    print(url.encode('utf-8', errors='replace'))
    print("--------------------------------------")

    # 3. Crear el engine como antes
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    # 4. Intentar la conexión (líneas 84-91)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
