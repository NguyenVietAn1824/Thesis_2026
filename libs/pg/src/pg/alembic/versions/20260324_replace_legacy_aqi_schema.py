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
    """Drop a column using raw SQL if it exists (idempotent).

    This migration is intended to clean up legacy AQI schema variants across
    different developer databases, so defensive DDL is preferred.
    """
    op.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column}')


def _add_column_if_not_exists(table: str, column: str, sql_type: str) -> None:
    """Add a column using raw SQL if it does not exist (idempotent)."""
    op.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}')


def upgrade() -> None:
    """Upgrade schema."""
    # Drop legacy constraints/indexes tied to old AQI schema.
    # These were created in `a0cff2a8a45b_initial_migration.py`.
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
    # Canonical schema source: `services/aqi_agent/.../shared/models/schemas.py`.
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

    # Ensure new GIS columns exist (for safety across inconsistent DB states).
    # provinces
    _add_column_if_not_exists('provinces', 'name_vi', 'VARCHAR(80)')
    _add_column_if_not_exists('provinces', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('provinces', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxy', 'DOUBLE PRECISION')

    # districts
    _add_column_if_not_exists('districts', 'province_id', 'TEXT')
    _add_column_if_not_exists('districts', 'name_vi', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxy', 'DOUBLE PRECISION')

    # distric_stats
    _add_column_if_not_exists('distric_stats', 'district_id', 'VARCHAR(50)')
    _add_column_if_not_exists('distric_stats', 'category_id', 'VARCHAR(50)')
    _add_column_if_not_exists('distric_stats', 'num', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_sum_pm25', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'val_avg_pm25', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'val_sum_aqi', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_avg_aqi', 'INTEGER')

    # Relax nullability/type to match imported dataset style.
    try:
        # Some DBs may have a leftover `province_id` column from older migrations.
        op.execute('ALTER TABLE provinces DROP COLUMN IF EXISTS province_id')
    except Exception as e:
        print(f"Skipping provinces.province_id drop: {e}")
    
    try:
        # Some DBs may have a leftover `district_id` column from older migrations.
        op.execute('ALTER TABLE districts DROP COLUMN IF EXISTS district_id')
    except Exception as e:
        print(f"Skipping districts.district_id drop: {e}")

    try:
        # `districts.province_id` references `provinces.id` (TEXT) and is nullable.
        op.execute('ALTER TABLE districts ALTER COLUMN province_id TYPE TEXT USING province_id::TEXT')
        op.execute('ALTER TABLE districts ALTER COLUMN province_id DROP NOT NULL')
    except Exception as e:
        print(f"Skipping districts.province_id alter: {e}")

    try:
        op.execute('ALTER TABLE distric_stats ALTER COLUMN district_id TYPE VARCHAR(50)')
        op.execute('ALTER TABLE distric_stats ALTER COLUMN district_id DROP NOT NULL')
    except Exception as e:
        print(f"Skipping distric_stats.district_id alter: {e}")


def downgrade() -> None:
    """Downgrade schema is intentionally not supported for destructive cleanup."""
    raise NotImplementedError('Downgrade is not supported for 20260324_replace_schema')
