from alembic import context
from app.storage_schema import metadata

connection = context.config.attributes.get("connection")
if connection is None:
    from app.config import settings
    from app.repository import SQLiteRepository
    repository = SQLiteRepository(settings.database_path)
    repository.path.parent.mkdir(parents=True, exist_ok=True)
    with repository.engine.begin() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
    repository.engine.dispose()
else:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
