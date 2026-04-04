from __future__ import annotations

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import RephraseServiceState
from aqi_agent.shared.settings import RephraseQuestionSettings
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompts import REPHRASE_SYSTEM_PROMPT
from .prompts import REPHRASE_USER_PROMPT

logger = get_logger(__name__)


class RephraseModel(BaseModel):
    """
    Model representing a rephrased question with context requirements.

    This model encapsulates the result of rephrasing a user's question,
    including whether the question requires additional context from the database.
    """
    rephrase_main_question: str | None = Field(
        ...,
        description=(
            'Rephrased main question; must stay in the same language as the user '
            '(Vietnamese in → Vietnamese out). Preserve Vietnamese place names exactly.'
        ),
    )
    need_context: bool = Field(
        ...,
        description='Indicates whether the rephrased question needs using context from database to answer the question.',
    )
    language: str = Field(
        ...,
        description='Primary language of the main question, e.g. Vietnamese or English.',
    )


class RephraseServiceInput(BaseModel):
    question: str
    conversation_history: list[CompletionMessage]
    summary: str


class RephraseServiceOutput(BaseModel):
    rephrased_main_question: str
    need_context: bool
    language: str


class RephraseService(BaseService):
    litellm_service: LiteLLMService
    settings: RephraseQuestionSettings

    @staticmethod
    def sanitize(content: str) -> str:
        """
        Sanitize question content by removing unnecessary whitespace.

        Removes leading and trailing whitespace and normalizes double newlines
        to single newlines to ensure clean input processing.

        Args:
            content: The raw question content to sanitize.

        Returns:
            The sanitized content string.

        Raises:
            ValueError: If the content is empty or None.
        """
        if not content:
            logger.error('Empty question content provided.')
            raise ValueError('Question content cannot be empty.')
        return content.strip().replace('\n\n', '\n')

    def preprocess_memory(
        self,
        question: str,
        recent_turns: list[CompletionMessage],
    ) -> str:
        """
        Preprocess conversation history and contextual information into formatted strings.

        Converts conversation turns into a structured text format and combines main
        information pieces into a single string for use in prompts.

        Args:
            question: The user's current question.
            recent_turns: List of recent conversation messages with roles and content.
            main_infos: List of contextual information strings.

        Returns:
            recent_turns_txt: Formatted conversation history as a string.

        Raises:
            ValueError: If no question is provided.
        """
        try:
            recent_turns_txt = '\n'.join(
                f'<{turn.role.value}>{self.sanitize(turn.content)}</{turn.role.value}>'
                for turn in recent_turns
            )
        except Exception as e:
            logger.exception(
                f'Failed conversation history conversion: {e}. Using raw text.',
                extra={'recent_turns': recent_turns},
            )
            recent_turns_txt = '\n'.join(str(turn) for turn in recent_turns)

        return recent_turns_txt

    async def process(self, inputs: RephraseServiceInput) -> RephraseServiceOutput:
        """
        Process a question rephrasing request using conversational context.

        Takes a user question along with conversation history and contextual information,
        then uses a language model to generate an improved rephrased question that
        better captures the user's intent and provides more context.

        Args:
            inputs: The input data containing the question, conversation history,
            and contextual information.

        Returns:
            A RephraseServiceOutput containing the rephrased question and a flag
            indicating whether additional context is needed.

        Raises:
            ValueError: If the input question is invalid or missing.
            Exception: If the LLM service fails to process the request.
        """
        recent_turns_txt = self.preprocess_memory(
            question=inputs.question,
            recent_turns=inputs.conversation_history,
        )
        message: list[CompletionMessage] = [
            CompletionMessage(
                role=MessageRole.SYSTEM,
                content=REPHRASE_SYSTEM_PROMPT,
            ),
            CompletionMessage(
                role=MessageRole.USER,
                content=REPHRASE_USER_PROMPT.format(
                    summary=inputs.summary,
                    recent_turns=recent_turns_txt,
                    question=inputs.question,
                ),
            ),
        ]
        try:
            response = await self.litellm_service.process_async(
                inputs=LiteLLMInput(
                    message=message,
                    return_type=RephraseModel,
                    frequency_penalty=self.settings.frequency_penalty,
                    n=self.settings.n,
                    model=self.settings.model,
                    presence_penalty=self.settings.presence_penalty,
                ),
            )
        except Exception as e:
            logger.exception('LLM processing failed', extra={'error': str(e)})
            raise e
        rephrase_result: RephraseModel = RephraseModel(**jsonable_encoder(response.response))
        logger.info(
            'Rephrase result',
            extra={
                'rephrase_main_question': rephrase_result.rephrase_main_question,
                'need_context': rephrase_result.need_context,
                'language': rephrase_result.language,
            },
        )
        return RephraseServiceOutput(
            rephrased_main_question=(
                rephrase_result.rephrase_main_question
                if rephrase_result.rephrase_main_question
                else inputs.question
            ),
            need_context=rephrase_result.need_context,
            language=rephrase_result.language,
        )

    async def gprocess(self, state: ChatwithDBState) -> dict:
        """Wrapper method for executing question rephrasing within the LangGraph state graph.

        Extracts necessary information from the state and returns the rephrased question
        along with context requirement as a dictionary.

        Args:
            state (ChatwithDBState): The state containing user question, conversation history, and summary.
        Returns:
            dict: Dictionary containing 'rephrased_main_question', 'need_context', and 'language'.
            Returns default values if processing fails.
        """
        try:
            rephrase_results = await self.process(
                inputs=RephraseServiceInput(
                    question=state.get('question', ''),
                    conversation_history=[CompletionMessage(**conversation_memory) for conversation_memory in state.get('conversation_memories', [])],
                    summary=state.get('conversation_summary', ''),
                ),
            )

            return {
                'rephrased_state': RephraseServiceState(
                    rephrased_main_question=rephrase_results.rephrased_main_question,
                    need_context=rephrase_results.need_context,
                    language=rephrase_results.language,
                ),
            }
        except Exception as e:
            logger.warning(
                'Failed to rephrase question in gprocess, using original question as fallback.',
                extra={
                    'error': str(e),
                    'original_question': state.get('question'),
                },
            )
            return {
                'rephrased_state': RephraseServiceState(
                    rephrased_main_question=state.get('question', ''),
                    need_context=False,
                    language='English',
                ),
            }
