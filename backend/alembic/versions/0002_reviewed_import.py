"""Preserve original reviewed CSV/XLSX files and import decisions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("uploads", sa.Column("original_file", sa.LargeBinary(), nullable=True))
    op.add_column("uploads", sa.Column("source_metadata", JSONB(), nullable=True))


def downgrade():
    op.drop_column("uploads", "source_metadata")
    op.drop_column("uploads", "original_file")
