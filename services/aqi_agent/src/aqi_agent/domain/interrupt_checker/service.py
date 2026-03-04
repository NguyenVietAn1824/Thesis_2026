from __future__ import annotations

from base import BaseModel
from base import BaseService
from aqi_agent.shared.models.state import ChatwithDBState
from logger import get_logger
from pg import SQLDatabase
from pg.controller.schemas import Conversation

logger = get_logger(__name__)


class InterruptCheckerInput(BaseModel):
    conversation_id: str
    user_id: str
    title: str
    summary: str


class InterruptCheckerOutput(BaseModel):
    interrupt: bool


class InterruptCheckerService(BaseService):
    sql_database: SQLDatabase

    async def process(self, inputs: InterruptCheckerInput) -> InterruptCheckerOutput:
        with self.sql_database.get_session() as session:
            converstaion = self.sql_database.get_conversation_by_id(session, inputs.conversation_id)
            if not converstaion:
                logger.warning(
                    f'Conversation with id {inputs.conversation_id} not found, creating a new one.',
                    extra={'conversation_id': inputs.conversation_id},
                )
                converstaion_model = Conversation(
                    id=inputs.conversation_id,
                    user_id=inputs.user_id,
                    title=inputs.title,
                    summary=inputs.summary,
                    is_confirming=False,
                )
                _ = self.sql_database.insert_conversation(session, converstaion_model)
                is_confirming = converstaion_model.is_confirming
            else:
                is_confirming = converstaion.is_confirming

        if is_confirming:
            logger.info(
                f'Conversation with id {inputs.conversation_id} is in confirming status, jump to the interrupted state.',
                extra={'conversation_id': inputs.conversation_id, 'is_confirming': is_confirming},
            )
        else:
            logger.info(
                f'Conversation with id {inputs.conversation_id} is not in confirming status, continuing the process.',
                extra={'conversation_id': inputs.conversation_id, 'is_confirming': is_confirming},
            )
        return InterruptCheckerOutput(interrupt=is_confirming)

    async def gprocess(self, state: ChatwithDBState) -> dict:
        try:
            inputs = InterruptCheckerInput(
                conversation_id=state.get('conversation_id', ''),
                user_id=state.get('user_id', ''),
                title=state.get('title', ''),
                summary=state.get('summary', ''),
            )
            output = await self.process(inputs)
            return {'interrupt': output.interrupt}
        except Exception as e:
            logger.exception(
                'Failed to construct InterruptCheckerInput from state, error: %s',
                extra={'error': str(e), 'state': state},
            )
            raise e
