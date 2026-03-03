from __future__ import annotations

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import PlannerServiceState
from aqi_agent.shared.models.state import SubTask
from aqi_agent.shared.settings import PlannerSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .models import PlannerModel
from .models import SubTaskModel
from .prompts import PLANNER_SYSTEM_PROMPT
from .prompts import PLANNER_USER_PROMPT

logger = get_logger(__name__)


class PlannerServiceInput(BaseModel):
    rephrased_question: str = Field(
        ...,
        description='The rephrased user question to plan for.',
    )
    conversation_history: list[CompletionMessage] = Field(
        default_factory=list,
        description='Recent conversation turns for context.',
    )
    conversation_summary: str = Field(
        default='',
        description='Summary of the conversation history.',
    )
    schema: str = Field(
        default='',
        description='Database schema information for context.',
    )
    additional_context: str = Field(
        default='',
        description='Any additional context relevant to planning.',
    )


class PlannerServiceOutput(BaseModel):
    subtasks: list[SubTaskModel] = Field(
        default_factory=list,
        description='List of ordered subtasks.',
    )
    requires_clarification: bool = Field(
        default=False,
        description='Whether clarification is required.',
    )
    planning_summary: str = Field(
        default='',
        description='Summary of the planning analysis.',
    )


class PlannerService(BaseService):
    """
    Planning Agent Service for Text-to-SQL systems.

    This service performs two key tasks simultaneously:
    1. Generates clarification questions for SQL generation (business formulas,
       concepts, abbreviations, ambiguities, etc.)
    2. Decomposes user queries into ordered subtasks for SQL generation.

    The service also acts as a debugging planner when provided with critics
    (error messages or feedback from failed SQL executions).
    """
    litellm_service: LiteLLMService
    settings: PlannerSettings

    @staticmethod
    def sanitize(content: str) -> str:
        """
        Sanitize content by removing unnecessary whitespace.

        Args:
            content: The raw content to sanitize.

        Returns:
            The sanitized content string.
        """
        if not content:
            return ''
        return content.strip().replace('\n\n', '\n')

    def _format_conversation_history(
        self,
        recent_turns: list[CompletionMessage],
    ) -> str:
        """
        Format conversation history into a structured text format.

        Args:
            recent_turns: List of recent conversation messages.

        Returns:
            Formatted conversation history as a string.
        """
        if not recent_turns:
            return 'No recent conversation history.'

        try:
            return '\n'.join(
                f'<{turn.role.value}>{self.sanitize(turn.content)}</{turn.role.value}>'
                for turn in recent_turns
            )
        except Exception as e:
            logger.exception(
                f'Failed conversation history conversion: {e}. Using raw text.',
                extra={'recent_turns': recent_turns},
            )
            return '\n'.join(str(turn) for turn in recent_turns)

    async def process(self, inputs: PlannerServiceInput) -> PlannerServiceOutput:
        """
        Process a planning request for query decomposition and clarification.

        Takes a rephrased user question along with context and generates
        clarification questions and ordered subtasks for SQL generation.

        Args:
            inputs: The input data containing the rephrased question,
                   conversation history, schema, and optional critics.

        Returns:
            A PlannerServiceOutput containing clarification questions,
            subtasks, and planning metadata.

        Raises:
            ValueError: If the input question is invalid or missing.
            Exception: If the LLM service fails to process the request.
        """
        recent_turns_txt = self._format_conversation_history(
            recent_turns=inputs.conversation_history,
        )

        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            schema=inputs.schema if inputs.schema else 'Schema not provided.',
        )

        # Build the user prompt
        user_prompt = PLANNER_USER_PROMPT.format(
            rephrased_question=inputs.rephrased_question,
            conversation_summary=inputs.conversation_summary or 'No summary available.',
            recent_turns=recent_turns_txt,
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
                return_type=PlannerModel,
                frequency_penalty=self.settings.frequency_penalty,
                n=self.settings.n,
                model=self.settings.model,
                presence_penalty=self.settings.presence_penalty,
            ),
        )

        planner_result: PlannerModel = PlannerModel(**jsonable_encoder(response.response))

        logger.info(
            'Planner result',
            extra={
                'num_subtasks': len(planner_result.subtasks),
                'requires_clarification': planner_result.requires_clarification,
                'planning_summary': planner_result.planning_summary,
            },
        )

        return PlannerServiceOutput(
            subtasks=planner_result.subtasks,
            requires_clarification=planner_result.requires_clarification,
            planning_summary=planner_result.planning_summary,
        )

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """
        Wrapper method for executing planning within the LangGraph state graph.

        Extracts necessary information from the state and returns the planning result
        as a dictionary compatible with the state graph.

        Args:
            state: The ChatwithDBState containing rephrased question, history, and context.

        Returns:
            dict: Dictionary containing 'planner_state' with the planning results.
                  Returns default values if processing fails.
        """
        try:
            rephrased_state = state.get('rephrased_state', {})
            rephrased_question = rephrased_state.get(
                'rephrased_main_question',
                state.get('question', ''),
            )

            history_state = state.get('history_retrieval_state', {})
            conversation_summary = history_state.get('conversation_summary', '')
            conversation_memories = history_state.get('conversation_memories', [])

            table_pruner_state = state.get('table_pruner_state', {})
            pruned_schema = table_pruner_state.get('pruned_schema', '')

            planner_results = await self.process(
                inputs=PlannerServiceInput(
                    rephrased_question=rephrased_question,
                    conversation_history=[
                        CompletionMessage(**mem) for mem in conversation_memories
                    ],
                    conversation_summary=conversation_summary,
                    schema=pruned_schema,
                ),
            )

            subtasks: list[SubTask] = [
                SubTask(
                    task_id=t.task_id,
                    description=t.description,
                    depends_on=t.depends_on,
                    sql_hint=t.sql_hint,
                )
                for t in planner_results.subtasks
            ]

            return {
                'planner_state': PlannerServiceState(
                    subtasks=subtasks,
                    requires_clarification=planner_results.requires_clarification,
                    planning_summary=planner_results.planning_summary,
                ),
            }
        except Exception as e:
            logger.warning(
                'Failed to process planning in gprocess, using fallback values.',
                extra={
                    'error': str(e),
                    'original_question': state.get('question'),
                },
            )
            return {
                'planner_state': PlannerServiceState(
                    subtasks=[
                        SubTask(
                            task_id='t1',
                            description='Execute the query directly',
                            depends_on=[],
                            sql_hint='Direct SQL generation',
                        ),
                    ],
                    requires_clarification=False,
                    planning_summary='Fallback plan due to processing error.',
                ),
            }
