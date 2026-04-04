from __future__ import annotations

"""Database utilities for CRUD operations.

This module provides generic utility functions for database operations following
the Repository pattern from sun_assistant. These utilities abstract common CRUD
operations to reduce boilerplate code in controller implementations.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..model import Base


def _insert(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    data: any,
) -> any:
    """Insert arbitrary data model into database.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class (e.g., DistrictModel)
        schema_cls: Pydantic schema class for validation (e.g., District)
        session: Active database session
        data: Pydantic schema instance containing data to insert

    Returns:
        Inserted data as Pydantic schema instance

    Raises:
        Exception: If database insertion fails

    Example:
        >>> district = District(id='001', name='Hoan Kiem')
        >>> result = _insert(logger, DistrictModel, District, session, district)
    """
    try:
        obj = model_cls(**data.model_dump(exclude_none=True))
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return schema_cls.model_validate(obj)
    except Exception as e:
        logger.exception('Failed to insert data', extra={'model': model_cls.__name__, 'error': str(e)})
        raise


def _update(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    data: any,
) -> any | None:
    """Update arbitrary data model in database.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class
        schema_cls: Pydantic schema class for validation
        session: Active database session
        data: Pydantic schema instance with updated data (must include id)

    Returns:
        Updated data as Pydantic schema instance, or None if no record found

    Raises:
        Exception: If database update fails

    Example:
        >>> district = District(id='001', name='Hoan Kiem Updated')
        >>> result = _update(logger, DistrictModel, District, session, district)
    """
    try:
        obj = session.get(model_cls, data.id)
        if obj:
            import sqlalchemy
            mapper = sqlalchemy.inspect(model_cls)
            column_names = [col.key for col in mapper.columns]

            for k, v in vars(data).items():
                if v is not None and k != 'id' and k in column_names:
                    setattr(obj, k, v)

            session.add(obj)
            session.commit()
            session.refresh(obj)
            return schema_cls.model_validate(obj)
        else:
            logger.info(f'No {schema_cls.__name__} found with id: {data.id}')
            return None
    except Exception as e:
        logger.exception('Failed to update data', extra={'model': model_cls.__name__, 'id': data.id, 'error': str(e)})
        raise


def _get_data(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    filter: dict[str, object] | None = None,
    order_by: Sequence | None = None,
    limit: int | None = None,
) -> list[any] | None:
    """Get arbitrary data with optional filtering, ordering, and limiting.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class
        schema_cls: Pydantic schema class for validation
        session: Active database session
        filter: Dictionary of filter conditions (column_name: value)
        order_by: Sequence of SQLAlchemy order_by clauses
        limit: Maximum number of results to return

    Returns:
        List of data as Pydantic schema instances, or None if no data found

    Raises:
        Exception: If database query fails

    Example:
        >>> districts = _get_data(logger, DistrictModel, District, session,
        ...                       filter={'province_id': '01'}, limit=10)
    """
    try:
        statement = select(model_cls)
        if filter:
            statement = statement.filter_by(**filter)
        if order_by:
            statement = statement.order_by(*order_by)
        if limit:
            statement = statement.limit(limit)
        
        objs = session.scalars(statement=statement).all()
        if len(objs) == 0:
            return None
        return [schema_cls.model_validate(obj) for obj in objs]
    except Exception as e:
        logger.exception('Failed to get data', extra={'model': model_cls.__name__, 'filter': filter, 'error': str(e)})
        raise


def _get_data_by_id(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    id: str | int,
) -> any | None:
    """Get arbitrary data by primary key ID.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class
        schema_cls: Pydantic schema class for validation
        session: Active database session
        id: Primary key value to search for

    Returns:
        Data as Pydantic schema instance, or None if not found

    Raises:
        Exception: If database query fails

    Example:
        >>> district = _get_data_by_id(logger, DistrictModel, District, session, '001')
    """
    try:
        obj = session.get(model_cls, id)
        if not obj:
            logger.debug(f'No {schema_cls.__name__} found with id: {id}')
            return None
        return schema_cls.model_validate(obj)
    except Exception as e:
        logger.exception('Failed to get data by id', extra={'model': model_cls.__name__, 'id': id, 'error': str(e)})
        raise


def _delete(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    id: str | int,
) -> any | None:
    """Delete arbitrary data by primary key ID.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class
        schema_cls: Pydantic schema class for validation
        session: Active database session
        id: Primary key value of record to delete

    Returns:
        Deleted data as Pydantic schema instance, or None if not found

    Raises:
        Exception: If database deletion fails

    Example:
        >>> deleted = _delete(logger, DistrictModel, District, session, '001')
    """
    try:
        obj = session.get(model_cls, id)
        if obj:
            session.delete(obj)
            session.commit()
            return schema_cls.model_validate(obj)
        else:
            logger.info(f'No {schema_cls.__name__} found with id: {id}')
            return None
    except Exception as e:
        logger.exception('Failed to delete data', extra={'model': model_cls.__name__, 'id': id, 'error': str(e)})
        raise


def _get_data_by_ids(
    logger,
    model_cls: type[Base],
    schema_cls: type,
    session: Session,
    ids: list[str | int],
) -> list[any] | None:
    """Get arbitrary data by list of primary key IDs.

    Args:
        logger: Structured logger for logging operations
        model_cls: SQLAlchemy ORM model class
        schema_cls: Pydantic schema class for validation
        session: Active database session
        ids: List of primary key values to fetch

    Returns:
        List of data as Pydantic schema instances, or None if none found

    Raises:
        Exception: If database query fails

    Example:
        >>> districts = _get_data_by_ids(logger, DistrictModel, District, 
        ...                              session, ['001', '002', '003'])
    """
    try:
        statement = select(model_cls).where(model_cls.id.in_(ids))
        objs = session.scalars(statement=statement).all()
        if len(objs) == 0:
            return None
        return [schema_cls.model_validate(obj) for obj in objs]
    except Exception as e:
        logger.exception('Failed to get data by ids', extra={'model': model_cls.__name__, 'ids': ids, 'error': str(e)})
        raise
