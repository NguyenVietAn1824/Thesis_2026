from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from base import BaseModel
from base import BaseService
from aqi_agent.domain.autocorrector import AutocorrectorService
from aqi_agent.domain.autocorrector.models import AutocorrectorInput
from aqi_agent.shared.models.state import ChatwithDBState
from lite_llm import LiteLLMService
from logger import get_logger

logger = get_logger(__name__)


class BaseSQLGeneratorServiceInput(BaseModel):
    question: str
    db_schema: str


class BaseSQLGeneratorServiceOutput(BaseModel):
    sql_query: str


class BaseSQLGeneratorService(BaseService, ABC):
    """
    Abstract base class for SQL generation strategies.

    All SQL generation strategies must inherit from this class and implement
    the `process` and `gprocess` methods.
    """
    litellm_service: LiteLLMService
    autocorrector_service: AutocorrectorService

    @abstractmethod
    async def generate_sql(self, inputs: BaseSQLGeneratorServiceInput) -> BaseSQLGeneratorServiceOutput:
        """
        Generate a SQL query from the given inputs.

        Args:
            inputs: BaseSQLGeneratorServiceInput containing the question and schema.

        Returns:
            BaseSQLGeneratorServiceOutput containing the generated SQL query.
        """
        raise NotImplementedError

    async def process(self, inputs: BaseSQLGeneratorServiceInput) -> BaseSQLGeneratorServiceOutput:
        """
        Generate a SQL query from the given inputs, then apply auto corrections.

        Args:
            inputs: SQLGeneratorServiceInput containing the question and schema.

        Returns:
            SQLGeneratorServiceOutput containing the generated SQL query.
        """
        try:
            output = await self.generate_sql(inputs)
            corrected_output = self.autocorrector_service.process(
                AutocorrectorInput(sql_query=output.sql_query),
            )

        except Exception as e:
            logger.exception(f'Error generating SQL: {e}')
            raise

        return BaseSQLGeneratorServiceOutput(sql_query=corrected_output.corrected_sql_query)

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """
        Wrapper method for executing SQL generation within the LangGraph state graph.

        Args:
            state: The current ChatwithDBState.

        Returns:
            dict containing the sql_generator_state.
        """
        raise NotImplementedError
