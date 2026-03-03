from __future__ import annotations

from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorService
from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorServiceInput
from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorServiceOutput
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import SQLGeneratorState
from aqi_agent.shared.settings import SQLGeneratorSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger

from .prompts import MATCH_GENERATOR_SYSTEM_PROMPT
from .prompts import MATCH_GENERATOR_USER_PROMPT

logger = get_logger(__name__)


class MatchSQLGeneratorServiceInput(BaseSQLGeneratorServiceInput):
    """
    Input model for the MatchGenerateStrategy.
    Extends BaseSQLGeneratorServiceInput with examples for few-shot prompting.
    """
    examples: list[dict]


class MatchSQLGeneratorServiceOutput(BaseSQLGeneratorServiceOutput):
    """
    Output model for the MatchGenerateStrategy.
    Currently identical to BaseSQLGeneratorServiceOutput but defined separately for clarity and future extensibility.
    """
    pass


class MatchSQLGeneratorService(BaseSQLGeneratorService):
    """
    SQL generator using few-shot example matching.

    This strategy uses retrieved similar examples to construct a few-shot prompt,
    combined with the pruned schema and rephrased question, to generate SQL queries.
    """
    litellm_service: LiteLLMService
    settings: SQLGeneratorSettings

    def _format_examples(self, examples: list[dict]) -> str:
        """
        Format a list of example question-SQL pairs into a string for the prompt.

        Args:
            examples: List of dicts with 'question' and 'sql_query' keys.

        Returns:
            Formatted string of examples.
        """
        if not examples:
            raise ValueError('No examples provided for formatting.')

        formatted_parts = []
        for i, example in enumerate(examples, 1):
            question = example.get('question', '')
            sql_query = example.get('sql_query', '')
            formatted_parts.append(
                f'<example-{i}>\n'
                f'  <question>{question}</question>\n'
                f'  <sql>{sql_query}</sql>\n'
                f'</example-{i}>',
            )
        return '\n'.join(formatted_parts)

    async def generate_sql(self, inputs: MatchSQLGeneratorServiceInput) -> MatchSQLGeneratorServiceOutput:
        """
        Generate a SQL query using few-shot example matching.

        Takes a rephrased question, pruned schema, and similar examples,
        then uses a language model to generate an appropriate SQL query.

        Args:
            inputs: MatchSQLGeneratorServiceInput containing the question, schema, and examples.

        Returns:
            MatchSQLGeneratorServiceOutput containing the generated SQL query.

        Raises:
            Exception: If the LLM service fails to process the request.
        """
        try:
            formatted_examples = self._format_examples(inputs.examples)
        except ValueError as e:
            logger.exception(
                'Error formatting examples for SQL generation.',
                extra={
                    'error': str(e),
                    'examples': inputs.examples,
                },
            )
            raise

        try:
            response = await self.litellm_service.process_async(
                inputs=LiteLLMInput(
                    message=[
                        CompletionMessage(
                            role=MessageRole.SYSTEM,
                            content=MATCH_GENERATOR_SYSTEM_PROMPT,
                        ),
                        CompletionMessage(
                            role=MessageRole.USER,
                            content=MATCH_GENERATOR_USER_PROMPT.format(
                                schema=inputs.db_schema,
                                examples=formatted_examples,
                                question=inputs.question,
                            ),
                        ),
                    ],
                    return_type=MatchSQLGeneratorServiceOutput,
                    frequency_penalty=self.settings.frequency_penalty,
                    n=self.settings.n,
                    model=self.settings.model,
                    presence_penalty=self.settings.presence_penalty,
                ),
            )

            return MatchSQLGeneratorServiceOutput(**jsonable_encoder(response.response))
        except Exception as e:
            logger.exception(
                'LLM processing error during sql match and generate process .',
                extra={
                    'error': str(e),
                    'question': inputs.question,
                    'db_schema': inputs.db_schema,
                    'examples': inputs.examples,
                },
            )
            raise

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """
        Wrapper method for executing SQL generation within the LangGraph state graph.

        Extracts the rephrased question, pruned schema, and retrieved examples from
        the state, then generates a SQL query.

        Args:
            state: The current ChatwithDBState containing rephrased question, pruned schema, and examples.

        Returns:
            dict containing the sql_generator_state with the generated SQL query.
            Returns empty query if processing fails.
        """
        try:
            rephrased_question = state.get('rephrased_state', {}).get('rephrased_main_question', '')
            pruned_schema = state.get('table_pruner_state', {}).get('pruned_schema', '')
            examples = state.get('example_retrieval_state', {}).get('examples', [])

            sql_result = await self.process(
                inputs=MatchSQLGeneratorServiceInput(
                    question=rephrased_question,
                    db_schema=pruned_schema,
                    examples=examples,
                ),
            )

            return {
                'sql_generator_state': SQLGeneratorState(
                    sql_query=sql_result.sql_query,
                ),
            }
        except Exception as e:
            logger.warning(
                'Failed to generate SQL in gprocess, returning empty query.',
                extra={
                    'error': str(e),
                    'question': state.get('rephrased_state', {}).get('rephrased_main_question', ''),
                },
            )
            return {
                'sql_generator_state': SQLGeneratorState(
                    sql_query='',
                ),
            }
