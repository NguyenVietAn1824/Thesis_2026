from __future__ import annotations

from typing import Optional

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.memory import Answer
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.models.memory import Question
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.settings import MemoryUpdaterSettings
from lite_llm import LiteLLMService
from logger import get_logger
from pg import SQLDatabase
from pg.controller.schemas import Conversation

from .conversation_summarizer import ConversationSummarizerInput
from .conversation_summarizer import ConversationSummarizerService
from .conversation_title_generator import ConversationTitleGeneratorInput
from .conversation_title_generator import ConversationTitleGeneratorService
from .upload_message_memory import UploadMessageMemoryInput
from .upload_message_memory import UploadMessageMemoryService

logger = get_logger(__name__)


class MemoryUpdaterInput(BaseModel):
    user_id: str
    conversation_id: str
    recent_messages: list[QAMemoryPair]
    qa_pair: QAMemoryPair
    additional_info: Optional[dict] = None


class MemoryUpdaterService(BaseService):
    """Main service for orchestrating all memory update operations."""

    litellm_service: LiteLLMService
    sql_database: SQLDatabase
    settings: MemoryUpdaterSettings

    @property
    def conversation_title_generator_service(self) -> ConversationTitleGeneratorService:
        return ConversationTitleGeneratorService(
            litellm=self.litellm_service,
            conversation_title_generator_settings=self.settings.conversation_title_generator,
        )

    @property
    def upload_message_memory_service(self) -> UploadMessageMemoryService:
        return UploadMessageMemoryService(
            sql_database=self.sql_database,
        )

    @property
    def conversation_summarizer_service(self) -> ConversationSummarizerService:
        return ConversationSummarizerService(
            litellm=self.litellm_service,
            conversation_summarizer_settings=self.settings.conversation_summarizer,
        )

    async def process(self, inputs: MemoryUpdaterInput) -> None:
        try:
            conversation_response = self.__get_conversation_title(
                conversation_id=inputs.conversation_id,
            )
        except Exception as e:
            logger.warning(
                'Failed to retrieve conversation title',
                extra={'error': str(e), 'conversation_id': inputs.conversation_id},
            )
            conversation_response = None

        if conversation_response is None:
            try:
                conversation_response = self.__create_conversation(
                    user_id=inputs.user_id,
                    conversation_id=inputs.conversation_id,
                )
            except Exception as e:
                logger.warning(
                    'Failed to create conversation',
                    extra={'error': str(e), 'user_id': inputs.user_id, 'conversation_id': inputs.conversation_id},
                )
                conversation_response = Conversation(
                    id=inputs.conversation_id,
                    user_id=inputs.user_id,
                    title='',
                    summary='',
                )

        if not conversation_response.title:
            if not inputs.qa_pair.qa_list or len(inputs.qa_pair.qa_list) < 2:
                qa_pair = QAMemoryPair(
                    qa_list=(Question(question=''), Answer(answer='')),
                )
            else:
                qa_pair = QAMemoryPair(
                    qa_list=(
                        Question(question=inputs.qa_pair.qa_list[0].question),
                        Answer(answer=inputs.qa_pair.qa_list[1].answer),
                    ),
                )
            try:
                conversation_response = (
                    await self.conversation_title_generator_service.process(
                        inputs=ConversationTitleGeneratorInput(qa_pair=qa_pair),
                    )
                )
            except Exception as e:
                logger.warning(
                    'Failed to generate conversation title',
                    extra={'error': str(e), 'conversation_id': inputs.conversation_id},
                )

        try:
            conversation_lastest_summary = self.__get_current_summary_from_conversation(
                conversation_id=inputs.conversation_id,
            )
        except Exception as e:
            logger.warning(
                'Failed to retrieve conversation summary',
                extra={'error': str(e), 'conversation_id': inputs.conversation_id},
            )
            conversation_lastest_summary = None

        try:
            conversation_summarizer_response = (
                await self.conversation_summarizer_service.process(
                    inputs=ConversationSummarizerInput(
                        latest_summary=conversation_lastest_summary or '',
                        latest_message=inputs.qa_pair,
                        recent_messages=inputs.recent_messages,
                    ),
                )
            )
            summary_attribute = conversation_summarizer_response.summary
        except Exception as e:
            logger.warning(
                'Failed to summarize conversation',
                extra={'error': str(e), 'conversation_id': inputs.conversation_id},
            )
            summary_attribute = conversation_lastest_summary or ''

        try:
            self.__update_conversation(
                conversation_id=inputs.conversation_id,
                summary=summary_attribute,
                title=conversation_response.title,
            )
        except Exception as e:
            logger.warning(
                'Failed to update conversation',
                extra={'error': str(e), 'conversation_id': inputs.conversation_id},
            )

        try:
            await self.upload_message_memory_service.process(
                inputs=UploadMessageMemoryInput(
                    conversation_id=inputs.conversation_id,
                    question=(
                        inputs.qa_pair.qa_list[0].question if inputs.qa_pair.qa_list else ''
                    ),
                    answer=(
                        inputs.qa_pair.qa_list[1].answer
                        if inputs.qa_pair.qa_list and len(inputs.qa_pair.qa_list) > 1
                        else ''
                    ),
                    conversation_title=conversation_response.title,
                    additional_info=inputs.additional_info,
                ),
            )
        except Exception as e:
            logger.warning(
                'Failed to upload message memory',
                extra={'error': str(e), 'conversation_id': inputs.conversation_id},
            )

    def __generate_additional_info(self, inputs: ChatwithDBState) -> dict:
        additional_info = {
            'language': inputs.get('rephrased_state', {}).get('language'),
            'rephrased_question': inputs.get('rephrased_state', {}).get('rephrased_main_question'),
        }
        return additional_info

    async def gprocess(self, inputs: ChatwithDBState) -> dict:
        recent_messages = self.__get_recent_messages(
            conversation_id=inputs.get('conversation_id'),
        )

        try:
            answer = inputs.get('answer_generator_state', {}).get('answer', '')
            if not answer:
                answer = inputs.get('human_intervent_state', {}).get('answer', '')
            await self.process(
                inputs=MemoryUpdaterInput(
                    user_id=inputs.get('user_id'),
                    conversation_id=inputs.get('conversation_id'),
                    recent_messages=recent_messages,
                    qa_pair=QAMemoryPair(
                        qa_list=(
                            Question(question=inputs.get('question')),
                            Answer(answer=answer),
                        ),
                    ),
                    additional_info=self.__generate_additional_info(inputs),
                ),
            )
            return {}
        except Exception as e:
            logger.warning(
                'Failed to update memory - data may not be persisted',
                extra={
                    'error': str(e),
                    'user_id': inputs.get('user_id'),
                    'conversation_id': inputs.get('conversation_id'),
                },
            )
            return {}

    def __get_conversation_title(self, conversation_id: str) -> Conversation | None:
        with self.sql_database.get_session() as session:
            conversation = self.sql_database.get_conversation_by_id(
                session=session, id=conversation_id,
            )
            return conversation

    def __get_current_summary_from_conversation(self, conversation_id: str) -> str | None:
        with self.sql_database.get_session() as session:
            conversation = self.sql_database.get_conversation_by_id(
                session=session, id=conversation_id,
            )
            return conversation.summary if conversation else None

    def __update_conversation(self, conversation_id: str, summary: str, title: str) -> None:
        with self.sql_database.get_session() as session:
            try:
                conversation = self.sql_database.get_conversation_by_id(
                    session=session, id=conversation_id,
                )
                if conversation:
                    conversation.summary = summary
                    conversation.title = title
                    self.sql_database.update_conversation(session=session, model=conversation)
            except Exception as e:
                raise e

    def __create_conversation(self, user_id: str, conversation_id: str) -> Conversation:
        with self.sql_database.get_session() as session:
            return self.sql_database.insert_conversation(
                session=session,
                model=Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title='',
                    summary='',
                ),
            )

    def __get_recent_messages(self, conversation_id: str) -> list[QAMemoryPair] | None:
        with self.sql_database.get_session() as session:
            messages_response = self.sql_database.get_messages(
                session=session,
                filter={'conversation_id': conversation_id},
                limit=self.settings.recent_messages,
            )

            if not messages_response:
                return []

            qa_pairs = []
            for message in messages_response:
                qa_pair = QAMemoryPair(
                    qa_list=(
                        Question(question=message.question),
                        Answer(answer=message.answer),
                    ),
                )
                qa_pairs.append(qa_pair)

            return qa_pairs
