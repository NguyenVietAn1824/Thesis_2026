from __future__ import annotations

from enum import Enum


class SQLExecutionMessage(str, Enum):
    SUCCESS = 'SQL execution successful.'
    EMPTY_QUERY = 'SQL query cannot be empty.'
    EXECUTION_FAILED = 'SQL execution failed: {error_message}'
    UNEXPECTED_ERROR = 'Unexpected error during SQL execution: {error_message}'
