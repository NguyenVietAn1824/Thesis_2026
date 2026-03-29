"""Update AQI schemas based on shared models.

Revision ID: 20260329_update_aqi_schemas
Revises: 20260324_replace_schema
Create Date: 2026-03-29 23:40:00.000000
"""

from typing import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260329_update_aqi_schemas'
down_revision: Union[str, Sequence[str], None] = '20260324_replace_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This migration is a safe, idempotent "cleanup" step. It is expected to run
    # after `20260324_replace_schema` and must NOT break if earlier migrations
    # already removed legacy columns.

    # provinces table: remove deprecated shadow id column if present.
    op.execute('DROP INDEX IF EXISTS idx_provinces_province_id')
    op.execute('ALTER TABLE provinces DROP COLUMN IF EXISTS province_id')

    # districts table: remove deprecated columns if present; ensure province_id is TEXT.
    op.execute('DROP INDEX IF EXISTS idx_districts_district_id')
    op.execute('ALTER TABLE districts DROP COLUMN IF EXISTS district_id')
    op.execute('ALTER TABLE districts DROP COLUMN IF EXISTS num_id')
    op.execute('ALTER TABLE districts ALTER COLUMN province_id TYPE TEXT USING province_id::TEXT')

    # distric_stats table: remove deprecated columns if present; ensure PM2.5 aggregates exist.
    op.execute('DROP INDEX IF EXISTS idx_distric_stats_num_id')
    op.execute('ALTER TABLE distric_stats DROP COLUMN IF EXISTS num_id')
    op.execute('ALTER TABLE distric_stats DROP COLUMN IF EXISTS val_sum')
    op.execute('ALTER TABLE distric_stats DROP COLUMN IF EXISTS val_avg')
    op.execute('ALTER TABLE distric_stats ADD COLUMN IF NOT EXISTS val_sum_pm25 DOUBLE PRECISION')
    op.execute('ALTER TABLE distric_stats ADD COLUMN IF NOT EXISTS val_avg_pm25 DOUBLE PRECISION')


def downgrade() -> None:
    """Downgrade schema."""
    # distric_stats table
    op.execute('ALTER TABLE distric_stats DROP COLUMN IF EXISTS val_avg_pm25')
    op.execute('ALTER TABLE distric_stats DROP COLUMN IF EXISTS val_sum_pm25')
    op.execute('ALTER TABLE distric_stats ADD COLUMN IF NOT EXISTS val_avg DOUBLE PRECISION')
    op.execute('ALTER TABLE distric_stats ADD COLUMN IF NOT EXISTS val_sum DOUBLE PRECISION')
    op.execute('ALTER TABLE distric_stats ADD COLUMN IF NOT EXISTS num_id INTEGER')
    op.execute('CREATE INDEX IF NOT EXISTS idx_distric_stats_num_id ON distric_stats (num_id)')

    # districts table
    op.execute('ALTER TABLE districts ALTER COLUMN province_id TYPE VARCHAR(80) USING province_id::VARCHAR')
    op.execute('ALTER TABLE districts ADD COLUMN IF NOT EXISTS num_id INTEGER')
    op.execute('ALTER TABLE districts ADD COLUMN IF NOT EXISTS district_id VARCHAR(80)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_districts_district_id ON districts (district_id)')

    # provinces table
    op.execute('ALTER TABLE provinces ADD COLUMN IF NOT EXISTS province_id VARCHAR(80)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_provinces_province_id ON provinces (province_id)')
