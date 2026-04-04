from __future__ import annotations

"""Pydantic schemas for database models.

This module defines Pydantic schemas that correspond to SQLAlchemy ORM models.
These schemas are used for:
1. Data validation when inserting/updating records
2. Serialization of database records to JSON
3. Type hints and IDE autocompletion
4. API request/response models

The schemas follow sun_assistant conventions with DatabaseSchema base class.
"""

from datetime import datetime
from datetime import date as date_type
from typing import Optional

from base import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Identified(BaseModel):
    """Base schema for models with ID field.

    Attributes:
        id: Primary key identifier (string or integer depending on model)
    """

    id: str | int


class Dated(BaseModel):
    """Base schema for models with timestamp fields.

    Attributes:
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
        deleted_at: Timestamp for soft delete
    """

    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class DatabaseSchema(Identified, Dated):
    """Base schema for all database models.

    Combines Identified and Dated to provide both ID and timestamp fields.
    Configures Pydantic to work with SQLAlchemy ORM models.
    """

    model_config = ConfigDict(
        from_attributes=True,  # Allow creating from SQLAlchemy models
        arbitrary_types_allowed=True,  # Allow complex types
    )


class Province(DatabaseSchema):
    """Province schema corresponding to provinces table.

    Attributes:
        id (str): Province identifier code
        name_vi (str | None): Province name in Vietnamese
        name_en (str | None): Province name in English
        type_vi (str | None): Province type in Vietnamese
        type_en (str | None): Province type in English
        extent_minx (float | None): Minimum X extent
        extent_maxx (float | None): Maximum X extent
        extent_miny (float | None): Minimum Y extent
        extent_maxy (float | None): Maximum Y extent
        districts (list[District] | None): Related districts (populated via relationship)
    """

    id: str  # type: ignore  # Override parent's id type
    name_vi: str | None = Field(default=None, description='Province name in Vietnamese')
    name_en: str | None = Field(default=None, description='Province name in English')
    type_vi: str | None = Field(default=None, description='Province type in Vietnamese')
    type_en: str | None = Field(default=None, description='Province type in English')
    extent_minx: float | None = Field(default=None, description='Minimum X extent')
    extent_maxx: float | None = Field(default=None, description='Maximum X extent')
    extent_miny: float | None = Field(default=None, description='Minimum Y extent')
    extent_maxy: float | None = Field(default=None, description='Maximum Y extent')

    # Relationships
    districts: Optional[list['District']] = Field(
        default=None,
        description='List of districts in this province',
    )


class District(DatabaseSchema):
    """District schema corresponding to districts table.

    Attributes:
        id (str): District identifier code
        province_id (str | None): Foreign key to provinces table
        name_vi (str | None): District name in Vietnamese
        name_en (str | None): District name in English
        type_vi (str | None): District type in Vietnamese
        type_en (str | None): District type in English
        extent_minx (float | None): Minimum X extent
        extent_maxx (float | None): Maximum X extent
        extent_miny (float | None): Minimum Y extent
        extent_maxy (float | None): Maximum Y extent
        province (Province | None): Related province (populated via relationship)
        stats (list[DistricStats] | None): Related statistics (populated via relationship)
    """

    id: str  # type: ignore  # Override parent's id type
    province_id: str | None = Field(
        default=None,
        description='Foreign key reference to provinces.id',
    )
    name_vi: str | None = Field(default=None, description='District name in Vietnamese')
    name_en: str | None = Field(default=None, description='District name in English')
    type_vi: str | None = Field(default=None, description='District type in Vietnamese')
    type_en: str | None = Field(default=None, description='District type in English')
    extent_minx: float | None = Field(default=None, description='Minimum X extent')
    extent_maxx: float | None = Field(default=None, description='Maximum X extent')
    extent_miny: float | None = Field(default=None, description='Minimum Y extent')
    extent_maxy: float | None = Field(default=None, description='Maximum Y extent')

    # Relationships
    province: Optional[Province] = Field(
        default=None,
        description='Related province record',
    )
    stats: Optional[list['DistricStats']] = Field(
        default=None,
        description='List of AQI statistics for this district',
    )


class AirComponent(DatabaseSchema):
    """Air component schema corresponding to air_component table.

    Represents measurable air quality components (e.g., PM2.5, PM10, O3, NO2).

    Attributes:
        id (int): Component identifier (auto-increment)
        name (str): Component name (e.g., 'PM2.5', 'AQI')
        description (str | None): Description of what this component measures
    """

    id: int  # type: ignore  # Override parent's id type
    name: str = Field(
        description='Air component name (e.g., PM2.5, AQI)',
    )
    description: str | None = Field(
        default=None,
        description='Description of the air component',
    )


class DistricStats(DatabaseSchema):
    """District statistics schema corresponding to distric_stats table.

    Attributes:
        id (int): Statistics record identifier (auto-increment)
        district_id (str | None): Foreign key to districts table
        category_id (str | None): Category identifier
        num (int | None): Number of measurements
        val_sum_pm25 (float | None): Sum of PM2.5 values
        val_avg_pm25 (float | None): Average of PM2.5 values
        val_sum_aqi (int | None): Sum of AQI values
        val_avg_aqi (int | None): Average of AQI values
    """

    id: int  # type: ignore  # Override parent's id type
    district_id: str | None = Field(default=None, description='Foreign key reference to districts.id')
    category_id: str | None = Field(default=None, description='Category identifier')
    num: int | None = Field(default=None, description='Number of measurements')
    val_sum_pm25: float | None = Field(default=None, description='Sum of PM2.5 values')
    val_avg_pm25: float | None = Field(default=None, description='Average of PM2.5 values')
    val_sum_aqi: int | None = Field(default=None, description='Sum of AQI values')
    val_avg_aqi: int | None = Field(default=None, description='Average of AQI values')


# Update forward references for relationships
Province.model_rebuild()
District.model_rebuild()
DistricStats.model_rebuild()


# ---------------------------------------------------------------------------
# User / Conversation / Message schemas
# ---------------------------------------------------------------------------


class User(DatabaseSchema):
    """User schema corresponding to user table.

    Attributes:
        id (str): User identifier
        full_name (str | None): Full name of the user
        email (str): Email address
        dob (datetime | None): Date of birth
        phone (str | None): Phone number
        gender (str | None): Gender
        avt_url (str | None): Avatar URL
        last_active (datetime): Last active timestamp
        role (str): User role
        status (str | None): User status
    """

    id: str  # type: ignore
    full_name: str | None = Field(default=None, description='Full name')
    email: str = Field(description='Email address')
    dob: datetime | None = Field(default=None, description='Date of birth')
    phone: str | None = Field(default=None, description='Phone number')
    gender: str | None = Field(default=None, description='Gender')
    avt_url: str | None = Field(default=None, description='Avatar URL')
    last_active: datetime | None = Field(default=None, description='Last active timestamp')
    role: str = Field(default='user', description='User role')
    status: str | None = Field(default=None, description='User status')


class UserAuthentication(DatabaseSchema):
    """User authentication schema corresponding to user_authentications table.

    Attributes:
        id (str): Authentication record identifier
        user_id (str): Foreign key to user table
        username (str): Username for login
        password (str): Hashed password
        social_id (str | None): Social login identifier
        mfa_enabled (bool): Whether MFA is enabled
    """

    id: str  # type: ignore
    user_id: str = Field(description='Foreign key to user table')
    username: str = Field(description='Username for login')
    password: str = Field(description='Hashed password')
    social_id: str | None = Field(default=None, description='Social login identifier')
    mfa_enabled: bool = Field(default=False, description='Whether MFA is enabled')


class Conversation(DatabaseSchema):
    """Conversation schema corresponding to conversation table.

    Attributes:
        id (str): Conversation identifier
        user_id (str): Foreign key to user table
        title (str): Title of the conversation
        summary (str): Summary of the conversation
        is_confirming (bool): Whether the conversation is in confirming state
    """

    id: str  # type: ignore
    user_id: str = Field(description='Foreign key to user table')
    title: str = Field(default='', description='Conversation title')
    summary: str = Field(default='', description='Conversation summary')
    is_confirming: bool = Field(default=False, description='Whether in confirming state')

    # Relationships
    messages: Optional[list['Message']] = Field(
        default=None,
        description='List of messages in this conversation',
    )


class Message(DatabaseSchema):
    """Message schema corresponding to message table.

    Attributes:
        id (str): Message identifier
        conversation_id (str): Foreign key to conversation table
        question (str): User question text
        answer (str): Assistant answer text
        additional_info (dict | None): Additional JSON metadata
    """

    id: str  # type: ignore
    conversation_id: str = Field(description='Foreign key to conversation table')
    question: str = Field(description='User question text')
    answer: str = Field(default='', description='Assistant answer text')
    additional_info: dict | None = Field(default=None, description='Additional JSON metadata')


# Rebuild all models for forward references
User.model_rebuild()
UserAuthentication.model_rebuild()
Conversation.model_rebuild()
Message.model_rebuild()
