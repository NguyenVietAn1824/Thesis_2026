from __future__ import annotations

import re

import sqlparse
from base import BaseModel
from base import BaseService
from chatwithdb.shared.models.state import ChatwithDBState
from chatwithdb.shared.models.state import SQLValidatorState
from logger import get_logger
from pydantic import Field
from sqlparse.sql import Statement

logger = get_logger(__name__)

# Dangerous SQL keywords that should be blocked
BLACKLIST_KEYWORDS = [
    'DROP',
    'TRUNCATE',
    'ALTER',
    'GRANT',
    'REVOKE',
    'DELETE',
    'INSERT',
    'UPDATE',
    'CREATE',
    'REPLACE',
    'MERGE',
    'CALL',
    'EXECUTE',
    'EXEC',
]


class SQLValidatorInput(BaseModel):
    """Input model for SQL validation."""
    sql_query: str = Field(..., description='The SQL query to validate')


class SQLValidatorOutput(BaseModel):
    """Output model for SQL validation."""
    is_valid: bool = Field(..., description='Whether the SQL query is valid and safe')
    error_message: str | None = Field(None, description='Error message if validation fails')
    sanitized_query: str | None = Field(None, description='Sanitized SQL query if valid')


class SQLValidatorService(BaseService):
    """
    Service for validating SQL queries to prevent dangerous operations.

    This service implements two validation layers:
    1. Blacklist Keywords: Checks for dangerous SQL keywords
    2. SQL Parser: Validates that only SELECT statements are allowed
    """

    def _check_blacklist_keywords(self, sql_query: str) -> tuple[bool, str | None]:
        """
        Check if SQL query contains any blacklisted keywords.

        Args:
            sql_query: The SQL query to check

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Convert to uppercase for case-insensitive matching
        sql_upper = sql_query.upper()

        for keyword in BLACKLIST_KEYWORDS:
            # Use word boundary to avoid false positives
            # e.g., don"t match "DROP" in "DROPDOWN"
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                error_msg = f'Dangerous keyword detected: {keyword}. Only SELECT queries are allowed.'
                logger.warning(
                    'Blacklist keyword detected',
                    extra={
                        'keyword': keyword,
                        'sql_query': sql_query,
                    },
                )
                return False, error_msg

        return True, None

    def _parse_and_validate_sql(self, sql_query: str) -> tuple[bool, str | None, str | None]:
        """
        Parse SQL query and validate it"s a SELECT statement.

        Args:
            sql_query: The SQL query to parse and validate

        Returns:
            Tuple of (is_valid, error_message, sanitized_query)
        """
        try:
            # Parse the SQL query
            parsed = sqlparse.parse(sql_query)

            if not parsed:
                return False, 'Empty or invalid SQL query.', None

            # Check each statement (in case of multiple statements)
            for statement in parsed:
                if not isinstance(statement, Statement):
                    continue

                # Get the statement type
                stmt_type = statement.get_type()

                # Only allow SELECT statements
                if stmt_type != 'SELECT':
                    error_msg = f'Only SELECT statements are allowed. Detected: {stmt_type}'
                    logger.warning(
                        'Non-SELECT statement detected',
                        extra={
                            'statement_type': stmt_type,
                            'sql_query': sql_query,
                        },
                    )
                    return False, error_msg, None

            # Format the SQL for better readability
            sanitized_query = sqlparse.format(
                sql_query,
                reindent=True,
                keyword_case='upper',
            )

            logger.info(
                'SQL query validated successfully',
                extra={
                    'original_query': sql_query,
                    'sanitized_query': sanitized_query,
                },
            )

            return True, None, sanitized_query

        except Exception as e:
            error_msg = f'Failed to parse SQL query: {str(e)}'
            logger.exception(
                'SQL parsing error',
                extra={
                    'sql_query': sql_query,
                    'error': str(e),
                },
            )
            return False, error_msg, None

    async def process(self, inputs: SQLValidatorInput) -> SQLValidatorOutput:
        """
        Validate SQL query through multiple security layers.

        This method performs the following validations:
        1. Checks for dangerous blacklisted keywords
        2. Parses and validates the SQL structure
        3. Ensures only SELECT statements are allowed

        Args:
            inputs: SQLValidatorInput containing the SQL query to validate

        Returns:
            SQLValidatorOutput with validation results
        """
        sql_query = inputs.sql_query.strip()

        if not sql_query:
            return SQLValidatorOutput(
                is_valid=False,
                error_message='SQL query cannot be empty.',
                sanitized_query=None,
            )

        # Step 1: Check blacklist keywords
        is_safe, blacklist_error = self._check_blacklist_keywords(sql_query)
        if not is_safe:
            return SQLValidatorOutput(
                is_valid=False,
                error_message=blacklist_error,
                sanitized_query=None,
            )

        # Step 2: Parse and validate SQL structure
        is_valid, parse_error, sanitized_query = self._parse_and_validate_sql(sql_query)
        if not is_valid:
            return SQLValidatorOutput(
                is_valid=False,
                error_message=parse_error,
                sanitized_query=None,
            )

        # All validations passed
        logger.info(
            'SQL query passed all validations',
            extra={'sql_query': sql_query},
        )

        return SQLValidatorOutput(
            is_valid=True,
            error_message=None,
            sanitized_query=sanitized_query,
        )

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """Wrapper method for executing SQL validation within the LangGraph state graph.

        Extracts necessary information from the state and returns the validation result.

        Args:
            state: The ChatwithDBState containing the SQL query to validate.
        Returns:
            dict: Dictionary containing 'sql_validator_state' with the validation results.
        """
        try:
            sql_query = state.get('sql_generator_state', {}).get('sql_query', '')

            output = await self.process(
                SQLValidatorInput(sql_query=sql_query),
            )

            return {
                'sql_validator_state': SQLValidatorState(
                    is_valid=output.is_valid,
                    error_message=output.error_message,
                    sanitized_query=output.sanitized_query,
                ),
            }

        except Exception as e:
            logger.warning(
                'SQL validation processing error',
                extra={
                    'error': str(e),
                },
            )
            return {
                'sql_validator_state': SQLValidatorState(
                    is_valid=False,
                    error_message='Sorry for the inconvenience, but I am unable to validate the SQL query at this time.',
                    sanitized_query=None,
                ),
            }
