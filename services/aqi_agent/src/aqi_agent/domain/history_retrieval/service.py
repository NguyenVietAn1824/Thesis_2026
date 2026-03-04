from __future__ import annotations

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.memory import Answer
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.models.memory import Question
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import HistoryRetrievalState
from aqi_agent.shared.settings.history_retrieval import HistoryRetrievalSettings
from fastapi.encoders import jsonable_encoder
from logger import get_logger
from pg import SQLDatabase
from pg.model import Message as MessageModel

logger = get_logger(__name__)


class HistoryRetrievalInput(BaseModel):
    conversation_id: str


class HistoryRetrievalOutput(BaseModel):
    conversation_memories: list[QAMemoryPair]
    conversation_summary: str


class HistoryRetrievalService(BaseService):
    sql_database: SQLDatabase
    settings: HistoryRetrievalSettings

    async def process(self, inputs: HistoryRetrievalInput) -> HistoryRetrievalOutput:
        try:
            conversation_memories = self.__get_conversation_memories(
                conversation_id=inputs.conversation_id,
            )
        except Exception as e:
            logger.exception('Error in HistoryRetrievalService: ', extra={'error': str(e)})
            conversation_memories = []

        try:
            conversation_summary = self.__get_conversation_summary(
                conversation_id=inputs.conversation_id,
            )
        except Exception as e:
            logger.exception('Error in HistoryRetrievalService: ', extra={'error': str(e)})
            conversation_summary = ''

        logger.info(
            'Retrieved conversation history',
            extra={
                'conversation_id': inputs.conversation_id,
                'num_conversation_memories': len(conversation_memories),
                'conversation_summary': conversation_summary,
            },
        )
        return HistoryRetrievalOutput(
            conversation_memories=conversation_memories,
            conversation_summary=conversation_summary,
        )

    def __get_conversation_memories(self, conversation_id: str) -> list[QAMemoryPair]:
        with self.sql_database.get_session() as session:
            messages = self.sql_database.get_messages(
                session=session,
                filter={'conversation_id': conversation_id},
                order_by=[MessageModel.created_at.desc()],
                limit=self.settings.n_turns,
            )

        qa_list: list[QAMemoryPair] = []
        if not messages:
            return qa_list

        for message in messages:
            rephrased_question = (
                message.additional_info['rephrased_question']
                if message.additional_info
                and 'rephrased_question' in message.additional_info
                else message.question
            )
            qa = QAMemoryPair(
                qa_list=(
                    Question(question=rephrased_question),
                    Answer(answer=message.answer),
                ),
            )
            qa_list.append(qa)

        return qa_list

    def __get_conversation_summary(self, conversation_id: str) -> str:
        with self.sql_database.get_session() as session:
            conversation = self.sql_database.get_conversation_by_id(
                session=session,
                id=conversation_id,
            )
            return conversation.summary if conversation else ''

    async def gprocess(self, state: ChatwithDBState) -> dict:
        try:
            inputs = HistoryRetrievalInput(conversation_id=state.get('conversation_id', ''))
            output = await self.process(inputs)
        except Exception as e:
            logger.exception('Error in HistoryRetrievalService: ', extra={'error': str(e)})
            return {
                'history_retrieval_state': HistoryRetrievalState(
                    conversation_memories=[],
                    conversation_summary='',
                ),
            }
        return {
            'history_retrieval_state': HistoryRetrievalState(
                conversation_memories=[jsonable_encoder(conversation_memory) for conversation_memory in output.conversation_memories],
                conversation_summary=output.conversation_summary,
            ),
        }
