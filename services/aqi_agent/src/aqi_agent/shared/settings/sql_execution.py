from __future__ import annotations

from base import BaseModel
from pydantic import Field


class SQLExecutionSettings(BaseModel):
    max_rows: int = Field(
        default=50,
        description="The maximum number of rows to return for a SQL query. If the result set exceeds this limit, only the first 'max_rows' will be returned along with an indication that there are more rows available.",
    )
    max_fix_retries: int = Field(
        default=3,
        description='Maximum number of retry attempts for fixing SQL queries.',
    )
