from __future__ import annotations

from datetime import datetime

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.state import AnswerGeneratorState
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.settings import AnswerGeneratorSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompts import ANSWER_GENERATOR_SYSTEM_PROMPT
from .prompts import ANSWER_GENERATOR_USER_PROMPT

logger = get_logger(__name__)


class AnswerGeneratorInput(BaseModel):
    question: str
    rephrased_question: str
    sql_query: str
    execution_result: str | None = None
    number_of_rows: int | None = None
    language: str = 'Vietnamese'
    conversation_summary: str | None = None
    conversation_memories: list[dict] | None = None


class AnswerGeneratorOutput(BaseModel):
    answer: str = Field(..., description='Natural language answer derived from SQL results')
    able_to_answer: bool = Field(
        default=True,
        description='Whether the question could be answered from the data',
    )


class AnswerGeneratorService(BaseService):
    """Service for generating natural language answers from SQL query results.

    Takes the user's question, the executed SQL query, and its results,
    then uses an LLM to produce a clear, human-readable response.

    Attributes:
        settings: Configuration settings for the answer generator.
        litellm_service: LLM service for generating responses.
    """

    model_config = {'arbitrary_types_allowed': True}

    settings: AnswerGeneratorSettings
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

    def _build_messages(self, inputs: AnswerGeneratorInput) -> list[CompletionMessage]:
        """Construct the message sequence for the LLM based on the input data."""
        conversation_history = self._prepare_conversation_history(
            inputs.conversation_memories,
            inputs.conversation_summary,
        )

        return [
            CompletionMessage(
                role=MessageRole.SYSTEM,
                content=ANSWER_GENERATOR_SYSTEM_PROMPT.format(
                    language=inputs.language,
                    date_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    display_rows=self.settings.display_rows,
                ),
            ),
            CompletionMessage(
                role=MessageRole.USER,
                content=ANSWER_GENERATOR_USER_PROMPT.format(
                    question=inputs.question,
                    rephrased_question=inputs.rephrased_question,
                    sql_query=inputs.sql_query,
                    execution_result=inputs.execution_result or 'No results',
                    number_of_rows=inputs.number_of_rows or 0,
                    conversation_history=conversation_history,
                ),
            ),
        ]

    async def _call_llm(self, messages: list[CompletionMessage]) -> AnswerGeneratorOutput | None:
        """Call LLM and return structured output, or None if response is invalid."""
        response = await self.litellm_service.process_async(
            inputs=LiteLLMInput(
                message=messages,
                model=self.settings.model,
                return_type=AnswerGeneratorOutput,
                frequency_penalty=self.settings.frequency_penalty,
                presence_penalty=self.settings.presence_penalty,
                n=self.settings.n,
                num_retry=self.settings.num_retry,
            ),
        )
        if isinstance(response.response, AnswerGeneratorOutput):
            return AnswerGeneratorOutput(**jsonable_encoder(response.response))
        return None

    async def process(self, inputs: AnswerGeneratorInput) -> AnswerGeneratorOutput:
        """Generate a natural language answer from SQL execution results.

        Retries are delegated to the LiteLLM service via num_retry setting.

        Args:
            inputs: AnswerGeneratorInput with question, SQL query, and execution results.

        Returns:
            AnswerGeneratorOutput with the generated answer and ability flag.
        """
        messages = self._build_messages(inputs)

        try:
            result = await self._call_llm(messages)
            if result is not None:
                return result

            logger.warning(
                'Invalid structured output from LLM',
                extra={'question': inputs.question},
            )

        except Exception as e:
            logger.exception(
                'Answer generation error',
                extra={
                    'question': inputs.question,
                    'error': str(e),
                },
            )

        return AnswerGeneratorOutput(
            answer='Xin lỗi, mình gặp sự cố khi xử lý kết quả. Bạn vui lòng thử lại nhé.',
            able_to_answer=False,
        )

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """Wrapper for LangGraph state graph execution."""
        try:
            rephrased_state = state.get('rephrased_state', {})
            history_state = state.get('history_retrieval_state', {})
            sql_generator_state = state.get('sql_generator_state', {})
            sql_execution_state = state.get('sql_execution_state', {})

            output = await self.process(
                AnswerGeneratorInput(
                    question=state.get('question', ''),
                    rephrased_question=rephrased_state.get('rephrased_main_question', ''),
                    sql_query=sql_generator_state.get('sql_query', ''),
                    execution_result=sql_execution_state.get('execution_result'),
                    number_of_rows=sql_execution_state.get('number_of_rows'),
                    language=rephrased_state.get('language', 'Vietnamese'),
                    conversation_summary=history_state.get('conversation_summary'),
                    conversation_memories=history_state.get('conversation_memories'),
                ),
            )

            return {
                'answer_generator_state': AnswerGeneratorState(
                    answer=output.answer,
                    able_to_answer=output.able_to_answer,
                ),
            }

        except Exception as e:
            logger.warning(
                'Answer generator gprocess error',
                extra={'error': str(e)},
            )
            return {
                'answer_generator_state': AnswerGeneratorState(
                    answer='Xin lỗi, mình không thể xử lý yêu cầu lúc này. Vui lòng thử lại.',
                    able_to_answer=False,
                ),
            }

    async def process_stream(self, inputs: AnswerGeneratorInput):
        """Stream the generated answer chunk by chunk."""
        logger.info(
            'Answer generation streaming started',
            extra={'question': inputs.question},
        )

        try:
            messages = self._build_messages(inputs)

            async for chunk in self.litellm_service.process_stream_async(
                inputs=LiteLLMInput(
                    message=messages,
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
                'Answer generation streaming error',
                extra={
                    'question': inputs.question,
                    'error': str(e),
                },
            )
            yield 'Xin lỗi, mình gặp sự cố khi xử lý kết quả. Bạn vui lòng thử lại nhé.'
