from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.base import Base

# Import all models so their tables register with Base.metadata.
import app.modules.fleet.models  # noqa: F401
import app.modules.users.models  # noqa: F401
import app.modules.routes.models  # noqa: F401
import app.modules.scheduling.models  # noqa: F401
import app.modules.avls.models  # noqa: F401
import app.modules.incidents.models  # noqa: F401
import app.modules.cms.models  # noqa: F401

# Import model modules here later so Alembic can detect their tables.
# Example: from app.modules.fleet import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

POSTGIS_MANAGED_TABLES = {
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
}


def include_name(name, type_, parent_names):
    
    if type_ == "schema":
        return name is None

    if type_ == "table":
        return name in target_metadata.tables

    return True


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=settings.database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()