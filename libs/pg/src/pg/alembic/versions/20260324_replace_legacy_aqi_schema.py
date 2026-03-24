"""Replace legacy AQI table schema with new GIS schema.

Revision ID: 20260324_replace_schema
Revises: 20260324_add_extent_fields
Create Date: 2026-03-24 00:30:00.000000
"""

from typing import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260324_replace_schema'
down_revision: Union[str, Sequence[str], None] = '20260324_add_extent_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_column_if_exists(table: str, column: str) -> None:
    op.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column}')


def upgrade() -> None:
    """Upgrade schema."""
    # Drop legacy constraints/indexes tied to old AQI schema.
    op.execute('ALTER TABLE distric_stats DROP CONSTRAINT IF EXISTS distric_stats_district_id_fkey')
    op.execute('ALTER TABLE districts DROP CONSTRAINT IF EXISTS districts_province_id_fkey')

    op.execute('DROP INDEX IF EXISTS idx_districts_admin_id')
    op.execute('DROP INDEX IF EXISTS idx_districts_name')
    op.execute('DROP INDEX IF EXISTS idx_districts_province')
    op.execute('DROP INDEX IF EXISTS idx_stats_component')
    op.execute('DROP INDEX IF EXISTS idx_stats_date')
    op.execute('DROP INDEX IF EXISTS idx_stats_date_district')
    op.execute('DROP INDEX IF EXISTS idx_stats_district')

    # Keep technical ids, replace old business columns by new GIS set.
    _drop_column_if_exists('provinces', 'name')

    _drop_column_if_exists('districts', 'name')
    _drop_column_if_exists('districts', 'normalized_name')
    _drop_column_if_exists('districts', 'administrative_id')
    _drop_column_if_exists('districts', 'created_at')
    _drop_column_if_exists('districts', 'updated_at')
    _drop_column_if_exists('districts', 'deleted_at')

    _drop_column_if_exists('distric_stats', 'date')
    _drop_column_if_exists('distric_stats', 'hour')
    _drop_column_if_exists('distric_stats', 'component_id')
    _drop_column_if_exists('distric_stats', 'aqi_value')
    _drop_column_if_exists('distric_stats', 'pm25_value')
    _drop_column_if_exists('distric_stats', 'created_at')
    _drop_column_if_exists('distric_stats', 'updated_at')
    _drop_column_if_exists('distric_stats', 'deleted_at')
    _drop_column_if_exists('distric_stats', 'extent_minx')
    _drop_column_if_exists('distric_stats', 'extent_maxx')
    _drop_column_if_exists('distric_stats', 'extent_miny')
    _drop_column_if_exists('distric_stats', 'extent_maxy')

    # Relax nullability/type to match imported dataset style.
    op.execute('ALTER TABLE provinces ALTER COLUMN province_id TYPE VARCHAR(80)')
    op.execute('ALTER TABLE districts ALTER COLUMN district_id TYPE VARCHAR(80)')
    op.execute('ALTER TABLE districts ALTER COLUMN province_id TYPE VARCHAR(80)')
    op.execute('ALTER TABLE distric_stats ALTER COLUMN district_id TYPE VARCHAR(50)')

    op.execute('ALTER TABLE districts ALTER COLUMN province_id DROP NOT NULL')
    op.execute('ALTER TABLE distric_stats ALTER COLUMN district_id DROP NOT NULL')


def downgrade() -> None:
    """Downgrade schema is intentionally not supported for destructive cleanup."""
    raise NotImplementedError('Downgrade is not supported for 20260324_replace_schema')
