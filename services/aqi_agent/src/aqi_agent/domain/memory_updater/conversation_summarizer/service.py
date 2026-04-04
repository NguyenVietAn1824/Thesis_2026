from __future__ import annotations

from typing import Optional

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.settings.memory_updater import ConversationSummarizerSettings
from aqi_agent.shared.utils import qa_message_to_string
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompt import CONVERSATION_SUMMARIZER_SYSTEM_PROMPT
from .prompt import CONVERSATION_SUMMARIZER_USER_PROMPT

logger = get_logger(__name__)


class ConversationSummarizerInput(BaseModel):
    latest_summary: Optional[str]
    latest_message: QAMemoryPair
    recent_messages: list[QAMemoryPair]


class ConversationSummarizerOutput(BaseModel):
    summary: str = Field(
        description=(
            'Updated conversation summary; same language as user; '
            'preserve Vietnamese place names exactly (diacritics, no romanization).'
        ),
    )


class ConversationSummarizerService(BaseService):
    litellm: LiteLLMService
    conversation_summarizer_settings: ConversationSummarizerSettings

    async def process(self, inputs: ConversationSummarizerInput) -> ConversationSummarizerOutput:
        all_messages = inputs.recent_messages + [inputs.latest_message]

        messages_str = qa_message_to_string(
            messages=all_messages,
        )

        message = [
            CompletionMessage(
                role=MessageRole.SYSTEM,
                content=CONVERSATION_SUMMARIZER_SYSTEM_PROMPT,
            ),
            CompletionMessage(
                role=MessageRole.USER,
                content=CONVERSATION_SUMMARIZER_USER_PROMPT.format(
                    summary=inputs.latest_summary,
                    recent_messages=messages_str,
                ),
            ),
        ]

        try:
            response = await self.litellm.process_async(
                inputs=LiteLLMInput(
                    message=message,
                    return_type=ConversationSummarizerOutput,
                    frequency_penalty=self.conversation_summarizer_settings.frequency_penalty,
                    n=self.conversation_summarizer_settings.n,
                    model=self.conversation_summarizer_settings.model,
                    presence_penalty=self.conversation_summarizer_settings.presence_penalty,
                ),
            )
            return ConversationSummarizerOutput(**jsonable_encoder(response.response))
        except Exception as e:
            logger.warning(
                'LLM processing error during conversation summarization',
                extra={'error': str(e)},
            )
            return ConversationSummarizerOutput(summary='')
