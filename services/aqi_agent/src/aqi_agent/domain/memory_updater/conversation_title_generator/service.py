from __future__ import annotations

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.settings.memory_updater import ConversationTitleGeneratorSettings
from aqi_agent.shared.utils import qa_message_to_string
from fastapi.encoders import jsonable_encoder
from lite_llm import CompletionMessage
from lite_llm import LiteLLMInput
from lite_llm import LiteLLMService
from lite_llm import MessageRole
from logger import get_logger
from pydantic import Field

from .prompt import CONVERSATION_TITLE_GENERATOR_SYSTEM_PROMPT
from .prompt import CONVERSATION_TITLE_GENERATOR_USER_PROMPT

logger = get_logger(__name__)


class ConversationTitleGeneratorInput(BaseModel):
    qa_pair: QAMemoryPair


class ConversationTitleGeneratorOutput(BaseModel):
    title: str = Field(
        description=(
            'Short title; same language as user; Vietnamese địa danh copied exactly from messages.'
        ),
    )


class ConversationTitleGeneratorService(BaseService):
    litellm: LiteLLMService
    conversation_title_generator_settings: ConversationTitleGeneratorSettings

    async def process(self, inputs: ConversationTitleGeneratorInput) -> ConversationTitleGeneratorOutput:
        messages_str = qa_message_to_string(
            messages=[inputs.qa_pair],
        )

        message = [
            CompletionMessage(
                role=MessageRole.SYSTEM,
                content=CONVERSATION_TITLE_GENERATOR_SYSTEM_PROMPT,
            ),
            CompletionMessage(
                role=MessageRole.USER,
                content=CONVERSATION_TITLE_GENERATOR_USER_PROMPT.format(
                    recent_messages=messages_str,
                ),
            ),
        ]

        try:
            response = await self.litellm.process_async(
                inputs=LiteLLMInput(
                    message=message,
                    return_type=ConversationTitleGeneratorOutput,
                    frequency_penalty=self.conversation_title_generator_settings.frequency_penalty,
                    n=self.conversation_title_generator_settings.n,
                    model=self.conversation_title_generator_settings.model,
                    presence_penalty=self.conversation_title_generator_settings.presence_penalty,
                ),
            )
            return ConversationTitleGeneratorOutput(**jsonable_encoder(response.response))
        except Exception as e:
            logger.warning(
                'LLM processing error during conversation title generation',
                extra={'error': str(e)},
            )
            return ConversationTitleGeneratorOutput(title='New Conversation')
