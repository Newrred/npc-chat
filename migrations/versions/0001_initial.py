"""Initial durable local schema."""
from alembic import op
from app.storage_schema import metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Destructive downgrade disabled. Restore a verified backup instead.")
