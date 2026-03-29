"""Align AQI geographic/statistic tables with imported GIS schema.

Revision ID: 20260324_add_extent_fields
Revises: 81eef9a67b62
Create Date: 2026-03-24 00:00:00.000000
"""

from typing import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260324_add_extent_fields'
down_revision: Union[str, Sequence[str], None] = '81eef9a67b62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_not_exists(table: str, column: str, sql_type: str) -> None:
    """Add a column using raw SQL if it does not exist.

    Why raw SQL: this migration is meant to be resilient across environments
    where the table may already exist with partial columns from earlier runs.
    """
    op.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}')


def _drop_column_if_exists(table: str, column: str) -> None:
    """Drop a column using raw SQL if it exists (idempotent)."""
    op.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column}')


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE:
    # This migration is aligned with `services/aqi_agent/.../shared/models/schemas.py`.
    # The canonical business identifiers are stored in `id` (TEXT) columns, so we do
    # NOT add shadow columns like `province_id` / `district_id`.

    # provinces: add GIS-oriented naming + extent fields.
    _add_column_if_not_exists('provinces', 'name_vi', 'VARCHAR(80)')
    _add_column_if_not_exists('provinces', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('provinces', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxy', 'DOUBLE PRECISION')

    # districts: add naming/type/extent fields. `province_id` already exists and is
    # used as the foreign reference to `provinces.id` (now nullable in later cleanup).
    _add_column_if_not_exists('districts', 'name_vi', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxy', 'DOUBLE PRECISION')

    # distric_stats: aggregate statistic columns (no extent columns here).
    _add_column_if_not_exists('distric_stats', 'num', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_sum_pm25', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'val_avg_pm25', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'category_id', 'VARCHAR(50)')
    _add_column_if_not_exists('distric_stats', 'val_sum_aqi', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_avg_aqi', 'INTEGER')

    # Index used by queries/filters in the new schema.
    op.execute('CREATE INDEX IF NOT EXISTS idx_distric_stats_category_id ON distric_stats (category_id)')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP INDEX IF EXISTS idx_distric_stats_category_id')

    for table in ['provinces', 'districts']:
        _drop_column_if_exists(table, 'extent_minx')
        _drop_column_if_exists(table, 'extent_maxx')
        _drop_column_if_exists(table, 'extent_miny')
        _drop_column_if_exists(table, 'extent_maxy')

    _drop_column_if_exists('provinces', 'name_vi')
    _drop_column_if_exists('provinces', 'name_en')
    _drop_column_if_exists('provinces', 'type_vi')
    _drop_column_if_exists('provinces', 'type_en')

    _drop_column_if_exists('districts', 'name_vi')
    _drop_column_if_exists('districts', 'name_en')
    _drop_column_if_exists('districts', 'type_vi')
    _drop_column_if_exists('districts', 'type_en')

    _drop_column_if_exists('distric_stats', 'num')
    _drop_column_if_exists('distric_stats', 'val_sum_pm25')
    _drop_column_if_exists('distric_stats', 'val_avg_pm25')
    _drop_column_if_exists('distric_stats', 'category_id')
    _drop_column_if_exists('distric_stats', 'val_sum_aqi')
    _drop_column_if_exists('distric_stats', 'val_avg_aqi')
