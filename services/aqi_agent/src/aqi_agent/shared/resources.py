from __future__ import annotations

from base import BaseModel
from lite_llm import LiteLLMService
from opensearch import OpenSearchService
from pg import SQLDatabase
from redis import Redis  # type: ignore[import-untyped]

from .settings import Settings


class Resources(BaseModel):
    settings: Settings
    litellm_service: LiteLLMService
    sql_database: SQLDatabase
    opensearch_service: OpenSearchService
    redis_client: Redis
