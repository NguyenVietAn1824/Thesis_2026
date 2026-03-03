from __future__ import annotations

from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorService
from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorServiceInput
from aqi_agent.domain.sql_generator.base import BaseSQLGeneratorServiceOutput
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import SQLGeneratorState
from aqi_agent.shared.models.state import SubTask
from aqi_agent.shared.settings.sql_generator import SQLGeneratorSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompts import MISMATCH_SQL_GENERATOR_SYSTEM_PROMPT
from .prompts import MISMATCH_SQL_GENERATOR_USER_PROMPT

logger = get_logger(__name__)


class MismatchSQLGeneratorServiceInput(BaseSQLGeneratorServiceInput):
    rephrased_question: str = Field(
        ...,
        description='The rephrased user question to generate SQL for.',
    )
    subtasks: list[SubTask] = Field(
        default_factory=list,
        description='List of subtasks decomposed from the user query.',
    )
    planning_summary: str = Field(
        default='',
        description='Summary of the planning analysis.',
    )
    examples: list[dict] = Field(
        default_factory=list,
        description='Retrieved examples for reference.',
    )
    additional_context: str = Field(
        default='',
        description='Any additional context relevant to SQL generation.',
    )


class MismatchSQLGeneratorServiceOutput(BaseSQLGeneratorServiceOutput):
    pass


class MismatchSQLGeneratorService(BaseSQLGeneratorService):
    """
    SQL Generator Service for Text-to-SQL systems.

    This service generates the final SQL query based on:
    - The rephrased user question
    - Decomposed subtasks from the planner
    - Database schema
    - Retrieved examples

    The service outputs a single, executable SQL query that fulfills
    all the requirements from the planning phase.
    """
    litellm_service: LiteLLMService
    settings: SQLGeneratorSettings

    def _format_subtasks(self, subtasks: list[SubTask]) -> str:
        """
        Format subtasks into a structured text format.

        Args:
            subtasks: List of subtasks from the planner.

        Returns:
            Formatted subtasks as a string.
        """
        if not subtasks:
            return 'No subtasks provided.'

        formatted_tasks = []
        for task in subtasks:
            task_str = (
                f"Task ID: {task.get('task_id', 'N/A')}\n"
                f"Description: {task.get('description', 'N/A')}\n"
                f"Depends On: {', '.join(task.get('depends_on', [])) or 'None'}\n"
                f"SQL Hint: {task.get('sql_hint', 'N/A')}"
            )
            formatted_tasks.append(task_str)

        return '\n\n'.join(formatted_tasks)

    def _format_examples(self, examples: list[dict]) -> str:
        """
        Format retrieved examples into a structured text format.

        Args:
            examples: List of retrieved examples.

        Returns:
            Formatted examples as a string.
        """
        if not examples:
            return ''

        formatted_examples = []
        for i, example in enumerate(examples, 1):
            example_str = (
                f'Example {i}:\n'
                f"Question: {example.get('question', 'N/A')}\n"
                f"SQL: {example.get('sql', 'N/A')}"
            )
            formatted_examples.append(example_str)

        return '\n\n'.join(formatted_examples)

    async def generate_sql(self, inputs: MismatchSQLGeneratorServiceInput) -> MismatchSQLGeneratorServiceOutput:
        """
        Process a SQL generation request.

        Takes the rephrased question, subtasks, schema, and examples to generate
        a final SQL query.

        Args:
            inputs: The input data containing the rephrased question,
                   subtasks, schema, and examples.

        Returns:
            A MismatchSQLGeneratorServiceOutput containing the generated SQL query
            and explanation.

        Raises:
            Exception: If the LLM service fails to process the request.
        """
        try:
            formatted_subtasks = self._format_subtasks(subtasks=inputs.subtasks)
        except Exception as e:
            logger.exception(
                'Error formatting subtasks for SQL generation.',
                extra={
                    'error': str(e),
                    'subtasks': inputs.subtasks,
                },
            )
            formatted_subtasks = ''

        try:
            formatted_examples = self._format_examples(examples=inputs.examples)
        except Exception as e:
            logger.exception(
                'Error formatting examples for SQL generation.',
                extra={
                    'error': str(e),
                    'examples': inputs.examples,
                },
            )
            formatted_examples = ''

        try:
            system_prompt = MISMATCH_SQL_GENERATOR_SYSTEM_PROMPT.format(
                schema=inputs.db_schema if inputs.db_schema else 'Schema not provided.',
                examples=formatted_examples,
            )

            user_prompt = MISMATCH_SQL_GENERATOR_USER_PROMPT.format(
                rephrased_question=inputs.rephrased_question,
                planning_summary=inputs.planning_summary or 'No planning summary available.',
                subtasks=formatted_subtasks,
                additional_context=inputs.additional_context or 'No additional context.',
            )

            messages: list[CompletionMessage] = [
                CompletionMessage(
                    role=MessageRole.SYSTEM,
                    content=system_prompt,
                ),
                CompletionMessage(
                    role=MessageRole.USER,
                    content=user_prompt,
                ),
            ]

            response = await self.litellm_service.process_async(
                inputs=LiteLLMInput(
                    message=messages,
                    return_type=MismatchSQLGeneratorServiceOutput,
                    frequency_penalty=self.settings.frequency_penalty,
                    n=self.settings.n,
                    model=self.settings.model,
                    presence_penalty=self.settings.presence_penalty,
                ),
            )

            return MismatchSQLGeneratorServiceOutput(**jsonable_encoder(response.response))
        except Exception as e:
            logger.exception(
                'Error during SQL generation with LLM service.',
                extra={
                    'error': str(e),
                    'rephrased_question': inputs.rephrased_question,
                    'planning_summary': inputs.planning_summary,
                    'subtasks': inputs.subtasks,
                    'db_schema': inputs.db_schema,
                },
            )
            raise e

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """
        Wrapper method for executing SQL generation within the LangGraph state graph.

        Extracts necessary information from the state and returns the SQL generation result
        as a dictionary compatible with the state graph.

        Args:
            state: The ChatwithDBState containing planner output, schema, and examples.

        Returns:
            dict: Dictionary containing 'sql_generator_state' with the SQL generation results.
                  Returns default values if processing fails.
        """
        try:
            rephrased_state = state.get('rephrased_state', {})
            rephrased_question = rephrased_state.get(
                'rephrased_main_question',
                state.get('question', ''),
            )

            planner_state = state.get('planner_state', {})
            subtasks = planner_state.get('subtasks', [])
            planning_summary = planner_state.get('planning_summary', '')

            table_pruner_state = state.get('table_pruner_state', {})
            pruned_schema = table_pruner_state.get('pruned_schema', '')

            example_retrieval_state = state.get('example_retrieval_state', {})
            examples = example_retrieval_state.get('examples', [])

            sql_results = await self.process(
                inputs=MismatchSQLGeneratorServiceInput(
                    question=state.get('question', ''),
                    rephrased_question=rephrased_question,
                    subtasks=subtasks,
                    planning_summary=planning_summary,
                    db_schema=pruned_schema,
                    examples=examples,
                ),
            )

            return {
                'sql_generator_state': SQLGeneratorState(
                    sql_query=sql_results.sql_query,
                ),
            }
        except Exception as e:
            logger.warning(
                'Failed to process SQL generation in gprocess, using fallback values.',
                extra={
                    'error': str(e),
                    'original_question': state.get('question'),
                    'rephrased_question': state.get('rephrased_state', {}).get('rephrased_main_question', ''),
                },
            )
            return {
                'sql_generator_state': SQLGeneratorState(
                    sql_query='',
                ),
            }
