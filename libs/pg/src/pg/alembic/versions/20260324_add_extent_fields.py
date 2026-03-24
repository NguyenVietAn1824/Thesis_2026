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
    op.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}')


def _drop_column_if_exists(table: str, column: str) -> None:
    op.execute(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {column}')


def upgrade() -> None:
    """Upgrade schema."""
    # provinces: keep existing columns and add GIS-oriented fields.
    _add_column_if_not_exists('provinces', 'province_id', 'VARCHAR(80)')
    _add_column_if_not_exists('provinces', 'name_vi', 'VARCHAR(80)')
    _add_column_if_not_exists('provinces', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('provinces', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('provinces', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('provinces', 'extent_maxy', 'DOUBLE PRECISION')

    # districts: add imported administrative naming and extent columns.
    _add_column_if_not_exists('districts', 'district_id', 'VARCHAR(80)')
    _add_column_if_not_exists('districts', 'name_vi', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'name_en', 'VARCHAR(150)')
    _add_column_if_not_exists('districts', 'type_vi', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'type_en', 'VARCHAR(50)')
    _add_column_if_not_exists('districts', 'num_id', 'INTEGER')
    _add_column_if_not_exists('districts', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('districts', 'extent_maxy', 'DOUBLE PRECISION')

    # distric_stats: add aggregate statistic columns from imported source.
    _add_column_if_not_exists('distric_stats', 'num_id', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_sum', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'num', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_avg', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'category_id', 'VARCHAR(50)')
    _add_column_if_not_exists('distric_stats', 'val_sum_aqi', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'val_avg_aqi', 'INTEGER')
    _add_column_if_not_exists('distric_stats', 'extent_minx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'extent_maxx', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'extent_miny', 'DOUBLE PRECISION')
    _add_column_if_not_exists('distric_stats', 'extent_maxy', 'DOUBLE PRECISION')

    op.execute('CREATE INDEX IF NOT EXISTS idx_provinces_province_id ON provinces (province_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_districts_district_id ON districts (district_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_distric_stats_num_id ON distric_stats (num_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_distric_stats_category_id ON distric_stats (category_id)')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP INDEX IF EXISTS idx_distric_stats_category_id')
    op.execute('DROP INDEX IF EXISTS idx_distric_stats_num_id')
    op.execute('DROP INDEX IF EXISTS idx_districts_district_id')
    op.execute('DROP INDEX IF EXISTS idx_provinces_province_id')

    for table in ['provinces', 'districts', 'distric_stats']:
        _drop_column_if_exists(table, 'extent_minx')
        _drop_column_if_exists(table, 'extent_maxx')
        _drop_column_if_exists(table, 'extent_miny')
        _drop_column_if_exists(table, 'extent_maxy')

    _drop_column_if_exists('provinces', 'province_id')
    _drop_column_if_exists('provinces', 'name_vi')
    _drop_column_if_exists('provinces', 'name_en')
    _drop_column_if_exists('provinces', 'type_vi')
    _drop_column_if_exists('provinces', 'type_en')

    _drop_column_if_exists('districts', 'district_id')
    _drop_column_if_exists('districts', 'name_vi')
    _drop_column_if_exists('districts', 'name_en')
    _drop_column_if_exists('districts', 'type_vi')
    _drop_column_if_exists('districts', 'type_en')
    _drop_column_if_exists('districts', 'num_id')

    _drop_column_if_exists('distric_stats', 'num_id')
    _drop_column_if_exists('distric_stats', 'val_sum')
    _drop_column_if_exists('distric_stats', 'num')
    _drop_column_if_exists('distric_stats', 'val_avg')
    _drop_column_if_exists('distric_stats', 'category_id')
    _drop_column_if_exists('distric_stats', 'val_sum_aqi')
    _drop_column_if_exists('distric_stats', 'val_avg_aqi')
