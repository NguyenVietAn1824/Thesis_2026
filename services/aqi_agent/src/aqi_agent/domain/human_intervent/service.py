from __future__ import annotations

from datetime import datetime

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import HumanInterventState
from aqi_agent.shared.settings import HumanInterventSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompts import HUMAN_INTERVENT_SYSTEM_PROMPT
from .prompts import HUMAN_INTERVENT_USER_PROMPT

logger = get_logger(__name__)


class HumanInterventInput(BaseModel):
    language: str
    rephrase_question: str
    planning_summary: str | None = None
    conversation_summary: str | None = None
    conversation_memories: list[dict] | None = None
    sql_validator_error: str | None = None
    sql_execution_exceeded_max_retries: bool | None = None
    no_relevant_schema: bool | None = None


class HumanInterventOutput(BaseModel):
    answer: str = Field(..., description='The final short reply to the user')


class HumanInterventService(BaseService):
    """Service for generating responses when database context is not needed."""
    model_config = {'arbitrary_types_allowed': True}

    settings: HumanInterventSettings
    litellm_service: LiteLLMService

    def _prepare_conversation_history(
        self,
        conversation_memories: list[dict] | None = None,
        conversation_summary: str | None = None,
    ) -> str:
        lines = []
        if conversation_memories:
            for memory in conversation_memories:
                role = memory.get('role', 'user')
                content = memory.get('content', '')
                lines.append(f'- {role.title()}: {content}')
        if conversation_summary:
            lines.append(f'- Summary: {conversation_summary}')
        return '\n'.join(lines)

    async def process(self, inputs: HumanInterventInput) -> HumanInterventOutput:
        """Processes the input query and generates an answer using the LLM service."""
        logger.info(
            'Human intervention processing started',
            extra={
                'rephrase_question': inputs.rephrase_question,
            },
        )
        try:
            conversation_history = self._prepare_conversation_history(
                inputs.conversation_memories,
                inputs.conversation_summary,
            )

            message = [
                CompletionMessage(
                    role=MessageRole.SYSTEM,
                    content=HUMAN_INTERVENT_SYSTEM_PROMPT.format(
                        language=inputs.language,
                        date_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    ),
                ),
                CompletionMessage(
                    role=MessageRole.USER,
                    content=HUMAN_INTERVENT_USER_PROMPT.format(
                        conversation_history=conversation_history,
                        rephrase_question=inputs.rephrase_question,
                        planning_summary=inputs.planning_summary or '',
                        sql_validator_error=inputs.sql_validator_error or '',
                        sql_execution_exceeded_max_retries=str(inputs.sql_execution_exceeded_max_retries or False).lower(),
                        no_relevant_schema=str(inputs.no_relevant_schema or False).lower(),
                    ),
                ),
            ]

            response = await self.litellm_service.process_async(
                inputs=LiteLLMInput(
                    message=message,
                    model=self.settings.model,
                    return_type=HumanInterventOutput,
                    frequency_penalty=self.settings.frequency_penalty,
                    presence_penalty=self.settings.presence_penalty,
                    n=self.settings.n,
                ),
            )

            if isinstance(response.response, HumanInterventOutput):
                return HumanInterventOutput(**jsonable_encoder(response.response))

        except Exception as e:
            logger.exception(
                'LLM processing error',
                extra={
                    'rephrase_question': inputs.rephrase_question,
                    'error': str(e),
                },
            )
        return HumanInterventOutput(
            answer='Xin lỗi, mình gặp sự cố khi xử lý yêu cầu. Bạn vui lòng thử lại nhé.',
        )

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """Wrapper method for executing human intervention within the LangGraph state graph.

        Extracts necessary information from the state and returns the generated answer.

        Args:
            state: The ChatwithDBState containing conversation context.

        Returns:
            dict: Dictionary containing human_intervent_state with the answer.
        """
        try:
            rephrased_state = state.get('rephrased_state', {})
            history_state = state.get('history_retrieval_state', {})
            planner_state = state.get('planner_state', {})
            sql_validator_state = state.get('sql_validator_state', {})

            need_context = rephrased_state.get('need_context', False)
            no_relevant_schema = (
                need_context
                and not state.get('table_pruner_state', {}).get('pruned_schema', '')
                and not state.get('example_retrieval_state', {}).get('examples', [])
            )

            output = await self.process(
                HumanInterventInput(
                    language=rephrased_state.get('language', 'Vietnamese'),
                    rephrase_question=rephrased_state.get('rephrased_main_question', state.get('question', '')),
                    conversation_summary=history_state.get('conversation_summary'),
                    conversation_memories=history_state.get('conversation_memories'),
                    planning_summary=planner_state.get('planning_summary'),
                    sql_validator_error=sql_validator_state.get('error_message') if sql_validator_state.get('is_valid') is False else None,
                    sql_execution_exceeded_max_retries=state.get('sql_execution_state', {}).get('exceeded_max_retries', False),
                    no_relevant_schema=no_relevant_schema,
                ),
            )

            return {
                'human_intervent_state': HumanInterventState(
                    answer=output.answer,
                ),
            }

        except Exception as e:
            logger.exception(
                'Human intervent processing error',
                extra={
                    'error': str(e),
                },
            )
            return {
                'human_intervent_state': HumanInterventState(
                    answer='Xin lỗi, mình không thể xử lý yêu cầu lúc này.',
                ),
            }

    async def process_stream(self, inputs: HumanInterventInput):
        """Process the input and stream the response."""
        logger.info(
            'Human intervention streaming started',
            extra={
                'rephrase_question': inputs.rephrase_question,
            },
        )

        try:
            conversation_history = self._prepare_conversation_history(
                inputs.conversation_memories,
                inputs.conversation_summary,
            )

            message = [
                CompletionMessage(
                    role=MessageRole.SYSTEM,
                    content=HUMAN_INTERVENT_SYSTEM_PROMPT.format(
                        language=inputs.language,
                        date_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    ),
                ),
                CompletionMessage(
                    role=MessageRole.USER,
                    content=HUMAN_INTERVENT_USER_PROMPT.format(
                        conversation_history=conversation_history,
                        rephrase_question=inputs.rephrase_question,
                        planning_summary=inputs.planning_summary or '',
                        sql_validator_error=inputs.sql_validator_error or '',
                        sql_execution_exceeded_max_retries=str(inputs.sql_execution_exceeded_max_retries or False).lower(),
                        no_relevant_schema=str(inputs.no_relevant_schema or False).lower(),
                    ),
                ),
            ]

            async for chunk in self.litellm_service.process_stream_async(
                inputs=LiteLLMInput(
                    message=message,
                    model=self.settings.model,
                    frequency_penalty=self.settings.frequency_penalty,
                    presence_penalty=self.settings.presence_penalty,
                    n=self.settings.n,
                    stream=True,
                    return_type=None,
                ),
            ):
                yield chunk

        except Exception as e:
            logger.exception(
                'Human intervent streaming error',
                extra={
                    'rephrase_question': inputs.rephrase_question,
                    'error': str(e),
                },
            )
            yield 'Xin lỗi, mình gặp sự cố khi xử lý yêu cầu. Bạn vui lòng thử lại nhé.'
