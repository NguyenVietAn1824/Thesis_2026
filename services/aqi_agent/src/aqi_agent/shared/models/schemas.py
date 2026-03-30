"""
Pydantic schemas aligned with PostgreSQL tables used by the AQI agent.

These mirror `libs/pg/src/pg/model.py` (provinces, districts, distric_stats, air_component).
Use `model_config` for ORM round-tripping where needed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from base import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Provinces(BaseModel):
    """Province row — table `provinces`."""

    model_config = ConfigDict(from_attributes=True)

    __tablename__ = 'provinces'

    id: str = Field(description='Primary key (text id)')
    name_vi: Optional[str] = Field(default=None, description='Name in Vietnamese (varchar 80)')
    name_en: Optional[str] = Field(default=None, description='Name in English (varchar 150)')
    type_vi: Optional[str] = Field(default=None, description='Administrative type, Vietnamese (varchar 50)')
    type_en: Optional[str] = Field(default=None, description='Administrative type, English (varchar 50)')
    extent_minx: Optional[float] = Field(default=None, description='Bounding box min longitude')
    extent_maxx: Optional[float] = Field(default=None, description='Bounding box max longitude')
    extent_miny: Optional[float] = Field(default=None, description='Bounding box min latitude')
    extent_maxy: Optional[float] = Field(default=None, description='Bounding box max latitude')

    districts: Optional[list[Districts]] = Field(
        default=None,
        description='Nested districts when loaded via GraphQL/ORM',
    )

class Districts(BaseModel):
    """District row — table `districts`."""

    model_config = ConfigDict(from_attributes=True)

    __tablename__ = 'districts'

    id: str = Field(description='Primary key (text id)')
    province_id: Optional[str] = Field(default=None, description='Province id (text id)')
    name_vi: Optional[str] = Field(default=None, description='Name in Vietnamese (varchar 150)')
    name_en: Optional[str] = Field(default=None, description='Name in English (varchar 150)')
    type_vi: Optional[str] = Field(default=None, description='Administrative type, Vietnamese')
    type_en: Optional[str] = Field(default=None, description='Administrative type, English')
    extent_minx: Optional[float] = Field(default=None, description='Bounding box min longitude')
    extent_maxx: Optional[float] = Field(default=None, description='Bounding box max longitude')
    extent_miny: Optional[float] = Field(default=None, description='Bounding box min latitude')
    extent_maxy: Optional[float] = Field(default=None, description='Bounding box max latitude')


class DistricStats(BaseModel):
    """District aggregate statistics — table `distric_stats`."""

    model_config = ConfigDict(from_attributes=True)

    __tablename__ = 'distric_stats'

    id: int = Field(description='Primary key (serial)')
    district_id: Optional[str] = Field(default=None, description='District code (varchar 50)')
    category_id: Optional[str] = Field(default=None, description='Category key e.g. mem_pm25_* (varchar 50)')
    num: Optional[int] = Field(default=None, description='Count used in aggregation')
    val_sum_pm25: Optional[float] = Field(default=None, description='Sum of PM25')
    val_avg_pm25: Optional[float] = Field(default=None, description='Average PM25')
    val_sum_aqi: Optional[int] = Field(default=None, description='Sum of AQI-scaled values')
    val_avg_aqi: Optional[int] = Field(default=None, description='Average AQI')

    district: Optional[Districts] = Field(
        default=None,
        description='Nested district when joined',
    )


class AirComponent(BaseModel):
    """Air component metadata — table `air_component`."""

    model_config = ConfigDict(from_attributes=True)

    __tablename__ = 'air_component'

    id: int = Field(description='Primary key')
    name: str = Field(description='Component name')
    description: Optional[str] = Field(default=None, description='Optional description')
    created_at: Optional[datetime] = Field(default=None, description='Created at')
    updated_at: Optional[datetime] = Field(default=None, description='Updated at')
    deleted_at: Optional[datetime] = Field(default=None, description='Soft delete timestamp')

Provinces.model_rebuild()
Districts.model_rebuild()
DistricStats.model_rebuild()
