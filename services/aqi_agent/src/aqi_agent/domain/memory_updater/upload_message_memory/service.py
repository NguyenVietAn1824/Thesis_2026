from __future__ import annotations

import uuid
from typing import Optional

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.memory import Answer
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.models.memory import Question
from logger import get_logger
from pg import SQLDatabase
from pg.controller.schemas import Message as MessageSchema

logger = get_logger(__name__)


class UploadMessageMemoryInput(BaseModel):
    conversation_id: str
    question: str
    answer: str
    conversation_title: Optional[str] = None
    additional_info: Optional[dict] = None


class UploadMessageMemoryService(BaseService):
    sql_database: SQLDatabase

    async def process(self, inputs: UploadMessageMemoryInput) -> QAMemoryPair:
        try:
            message = MessageSchema(
                id=str(uuid.uuid4()),
                conversation_id=inputs.conversation_id,
                question=inputs.question,
                answer=inputs.answer,
                additional_info=inputs.additional_info,
            )
            with self.sql_database.get_session() as session:
                self.sql_database.insert_message(session=session, model=message)

            logger.info(
                'Message memory uploaded successfully',
                extra={
                    'conversation_id': inputs.conversation_id,
                    'message_id': message.id,
                    "answer": inputs.answer,
                    "question": inputs.question,
                },
            )

            return QAMemoryPair(
                qa_list=(
                    Question(question=inputs.question),
                    Answer(answer=inputs.answer),
                ),
            )
        except Exception as e:
            logger.error(
                'Failed to upload message memory',
                extra={
                    'conversation_id': inputs.conversation_id,
                    'error': str(e),
                },
            )
            return QAMemoryPair(
                qa_list=(
                    Question(question=inputs.question),
                    Answer(answer=inputs.answer),
                ),
            )
