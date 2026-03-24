"""
Hasura GraphQL selector schemas for KLTN AQI system.

Each field is a boolean selector:
- False: do not include column in GraphQL selection set
- True: include column in GraphQL selection set

Relationship fields are nested objects (or None).
"""

from typing import Optional

from base import BaseModel
from pydantic import Field


class Provinces(BaseModel):
    """Provinces administrative table."""

    __tablename__ = 'provinces'

    id: bool = Field(default=False, description='Row identifier')
    province_id: bool = Field(default=False, description='Province code/id from source dataset')
    name_vi: bool = Field(default=False, description='Vietnamese province name')
    name_en: bool = Field(default=False, description='English/ASCII province name')
    type_vi: bool = Field(default=False, description='Administrative type in Vietnamese')
    type_en: bool = Field(default=False, description='Administrative type in English')
    extent_minx: bool = Field(default=False, description='Geometry extent min X')
    extent_miny: bool = Field(default=False, description='Geometry extent min Y')
    extent_maxx: bool = Field(default=False, description='Geometry extent max X')
    extent_maxy: bool = Field(default=False, description='Geometry extent max Y')

    districts: Optional['Districts'] = Field(
        default=None,
        description='Districts belonging to this province',
    )


class Districts(BaseModel):
    """Districts administrative table."""

    __tablename__ = 'districts'

    id: bool = Field(default=False, description='Row identifier')
    district_id: bool = Field(default=False, description='District code/id from source dataset')
    name_vi: bool = Field(default=False, description='Vietnamese district name')
    name_en: bool = Field(default=False, description='English/ASCII district name')
    type_vi: bool = Field(default=False, description='Administrative type in Vietnamese')
    type_en: bool = Field(default=False, description='Administrative type in English')
    province_id: bool = Field(default=False, description='Province code/id this district belongs to')
    num_id: bool = Field(default=False, description='Numeric district id from GIS source')
    extent_minx: bool = Field(default=False, description='Geometry extent min X')
    extent_miny: bool = Field(default=False, description='Geometry extent min Y')
    extent_maxx: bool = Field(default=False, description='Geometry extent max X')
    extent_maxy: bool = Field(default=False, description='Geometry extent max Y')


class DistricStats(BaseModel):
    """District statistics aggregate table."""

    __tablename__ = 'distric_stats'

    id: bool = Field(default=False, description='Row identifier')
    num_id: bool = Field(default=False, description='Numeric district identifier')
    district_id: bool = Field(default=False, description='District code/id')
    val_sum: bool = Field(default=False, description='Sum of measured values')
    num: bool = Field(default=False, description='Count of records used in aggregation')
    val_avg: bool = Field(default=False, description='Average value')
    category_id: bool = Field(default=False, description='Aggregation category id')
    val_sum_aqi: bool = Field(default=False, description='Sum AQI value')
    val_avg_aqi: bool = Field(default=False, description='Average AQI value')

    district: Optional['Districts'] = Field(
        default=None,
        description='Nested district relationship',
    )


class AirComponent(BaseModel):
    """Air component metadata table."""

    __tablename__ = 'air_component'

    id: bool = Field(default=False, description='Unique identifier')
    name: bool = Field(default=False, description='Air component name')
    description: bool = Field(default=False, description='Component description')
    created_at: bool = Field(default=False, description='Created timestamp')
    updated_at: bool = Field(default=False, description='Updated timestamp')
    deleted_at: bool = Field(default=False, description='Deleted timestamp')


class Tables(BaseModel):
    """Container for all available tables."""

    provinces: Provinces = Field(
        default_factory=Provinces,
        description='Provinces table',
    )
    districts: Districts = Field(
        default_factory=Districts,
        description='Districts table',
    )
    distric_stats: DistricStats = Field(
        default_factory=DistricStats,
        description='District statistics table',
    )
    air_component: AirComponent = Field(
        default_factory=AirComponent,
        description='Air component table',
    )
