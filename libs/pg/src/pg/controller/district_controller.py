from __future__ import annotations

"""District controller for database operations.

This module provides CRUD operations for the districts table following
the sun_assistant Repository pattern. Includes specialized queries for
district search and filtering.
"""

from collections.abc import Sequence
from functools import partial
from typing import cast

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from ..model import District as DistrictModel
from .repository import Repository
from .schemas import District
from .utils import _delete
from .utils import _get_data
from .utils import _get_data_by_id
from .utils import _insert
from .utils import _update

# Simple logger for this module
class SimpleLogger:
    def info(self, msg, **kwargs):
        print(f"INFO: {msg}")
    def debug(self, msg, **kwargs):
        pass
    def exception(self, msg, **kwargs):
        print(f"ERROR: {msg}")

logger = SimpleLogger()

# Create partial functions
_insert_method = partial(_insert, logger, DistrictModel, District)
_update_method = partial(_update, logger, DistrictModel, District)
_delete_method = partial(_delete, logger, DistrictModel, District)
_get_method = partial(_get_data, logger, DistrictModel, District)
_get_by_id_method = partial(_get_data_by_id, logger, DistrictModel, District)


class DistrictController(Repository):
    """Controller for district database operations.

    Provides CRUD operations plus specialized queries for district search,
    filtering by province, and normalized name matching.
    """

    def insert_district(self, session: Session, model: District) -> District:
        """Insert a new district record."""
        return cast(District, _insert_method(session, model))

    def update_district(self, session: Session, model: District) -> District | None:
        """Update an existing district record."""
        result = _update_method(session, model)
        return cast(District, result) if result else None

    def delete_district(self, session: Session, id: str) -> District | None:
        """Delete a district by ID."""
        result = _delete_method(session, id)
        return cast(District, result) if result else None

    def get_districts(
        self,
        session: Session,
        filter: dict[str, object] | None = None,
        order_by: Sequence | None = None,
        limit: int | None = None,
    ) -> list[District] | None:
        """Get districts with optional filtering and ordering."""
        result = _get_method(session, filter, order_by, limit)
        return cast(list[District], result) if result else None

    def get_district_by_id(self, session: Session, id: str) -> District | None:
        """Get a district by its ID."""
        result = _get_by_id_method(session, id)
        return cast(District, result) if result else None

    # SPECIALIZED QUERIES

    def search_districts_by_name(
        self,
        session: Session,
        search_term: str,
        limit: int = 10,
    ) -> list[District] | None:
        """Search districts by name or normalized name (case-insensitive).

        Args:
            session: Active database session
            search_term: Term to search for in district names
            limit: Maximum number of results (default: 10)

        Returns:
            List of matching districts, or None if none found

        Example:
            >>> # Find districts containing "Hoàn Kiếm"
            >>> districts = controller.search_districts_by_name(session, "hoan kiem")
        """
        try:
            stmt = select(DistrictModel).where(
                or_(
                    DistrictModel.name_vi.ilike(f'%{search_term}%'),
                    DistrictModel.name_en.ilike(f'%{search_term}%'),
                )
            ).limit(limit)
            
            objs = session.scalars(stmt).all()
            if len(objs) == 0:
                return None
            return [District.model_validate(obj) for obj in objs]
        except Exception as e:
            logger.exception('Failed to search districts', extra={'search_term': search_term, 'error': str(e)})
            raise

    def get_districts_by_province(
        self,
        session: Session,
        province_id: str,
    ) -> list[District] | None:
        """Get all districts in a specific province.

        Args:
            session: Active database session
            province_id: Province ID to filter by

        Returns:
            List of districts in the province, or None if none found

        Example:
            >>> # Get all districts in Hanoi
            >>> districts = controller.get_districts_by_province(session, '01')
        """
        return self.get_districts(
            session=session,
            filter={'province_id': province_id},
            order_by=[DistrictModel.name_vi],
        )

    def get_district_by_normalized_name(
        self,
        session: Session,
        normalized_name: str,
    ) -> District | None:
        """Get a district by exact normalized name match.

        Args:
            session: Active database session
            normalized_name: Exact normalized name to match

        Returns:
            District if found, None otherwise

        Example:
            >>> district = controller.get_district_by_normalized_name(session, 'hoan kiem')
        """
        try:
            stmt = select(DistrictModel).where(
                DistrictModel.name_vi.ilike(normalized_name)
            )
            obj = session.scalars(stmt).first()
            return District.model_validate(obj) if obj else None
        except Exception as e:
            logger.exception('Failed to get district by normalized name', 
                           extra={'normalized_name': normalized_name, 'error': str(e)})
            raise
