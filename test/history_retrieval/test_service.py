"""
Integration tests for HistoryRetrievalService.

These tests connect to a real PostgreSQL database and test the
HistoryRetrievalService.process() and gprocess() methods using a real
conversation_id from the database.

Run with:
    pytest test/history_retrieval/test_service.py -v -s
    pytest test/history_retrieval/test_service.py -v -k "unit"          # unit tests only
    pytest test/history_retrieval/test_service.py -v -k "integration"   # integration tests
"""
from __future__ import annotations

import os

import pytest
from dotenv import find_dotenv, load_dotenv

# Load project .env so POSTGRES__* vars are available
load_dotenv(find_dotenv('.env'), override=True)

from pg import SQLDatabase
from pg.model import Message as MessageModel
from aqi_agent.domain.history_retrieval.service import (
    HistoryRetrievalInput,
    HistoryRetrievalOutput,
    HistoryRetrievalService,
)
from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.settings.history_retrieval import HistoryRetrievalSettings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PG_USERNAME = os.getenv('POSTGRES__USERNAME', 'hanoiair_user')
PG_PASSWORD = os.getenv('POSTGRES__PASSWORD', 'hanoiair_pass')
PG_HOST = os.getenv('POSTGRES__HOST', 'localhost')
PG_PORT = int(os.getenv('POSTGRES__PORT', '15432'))
PG_DB = os.getenv('POSTGRES__DB', 'hanoiair_db')

# ⬇️  Set the conversation_id you want to test with here
CONVERSATION_ID = os.getenv('TEST_CONVERSATION_ID', '')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_output(test_name: str, result: HistoryRetrievalOutput) -> None:
    """Pretty-print the history retrieval output (visible with pytest -s)."""
    border = '=' * 80
    print(f'\n{border}')
    print(f'  HISTORY RETRIEVAL OUTPUT — {test_name}')
    print(border)
    print(f'  conversation_summary : {result.conversation_summary!r}')
    print(f'  conversation_memories ({len(result.conversation_memories)}):')
    for i, mem in enumerate(result.conversation_memories, 1):
        if mem.qa_list:
            print(f'    [{i}] Q: {mem.qa_list[0].question}')
            print(f'         A: {mem.qa_list[1].answer[:120]}...' if len(mem.qa_list[1].answer) > 120 else f'         A: {mem.qa_list[1].answer}')
        else:
            print(f'    [{i}] (empty)')
    print(border + '\n')


def _log_gprocess_output(test_name: str, result: dict) -> None:
    """Pretty-print the gprocess output (visible with pytest -s)."""
    border = '=' * 80
    print(f'\n{border}')
    print(f'  GPROCESS OUTPUT — {test_name}')
    print(border)
    hs = result.get('history_retrieval_state', {})
    print(f'  conversation_summary : {hs.get("conversation_summary", "")!r}')
    memories = hs.get('conversation_memories', [])
    print(f'  conversation_memories ({len(memories)}):')
    for i, mem in enumerate(memories, 1):
        qa = mem.get('qa_list') or mem
        if isinstance(qa, (list, tuple)) and len(qa) == 2:
            print(f'    [{i}] Q: {qa[0].get("question", qa[0]) if isinstance(qa[0], dict) else qa[0]}')
            ans = qa[1].get('answer', qa[1]) if isinstance(qa[1], dict) else qa[1]
            print(f'         A: {str(ans)[:120]}...' if len(str(ans)) > 120 else f'         A: {ans}')
        else:
            print(f'    [{i}] {mem}')
    print(border + '\n')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def sql_database() -> SQLDatabase:
    """Create a real SQLDatabase connection to PostgreSQL."""
    return SQLDatabase(
        username=PG_USERNAME,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT,
        db=PG_DB,
    )


@pytest.fixture(scope='module')
def history_settings() -> HistoryRetrievalSettings:
    """Create history retrieval settings with n_turns = 2."""
    return HistoryRetrievalSettings(n_turns=2)


@pytest.fixture(scope='module')
def history_service(sql_database, history_settings) -> HistoryRetrievalService:
    """Create the HistoryRetrievalService wired to the real database."""
    return HistoryRetrievalService(
        sql_database=sql_database,
        settings=history_settings,
    )


@pytest.fixture(scope='module')
def conversation_id(sql_database) -> str:
    """
    Return a valid conversation_id from the database.

    Priority:
      1. The TEST_CONVERSATION_ID env var (if set).
      2. The first conversation found in the database.

    Skips if no conversation is available.
    """
    if CONVERSATION_ID:
        return CONVERSATION_ID

    with sql_database.get_session() as session:
        conversation = sql_database.get_conversations(session=session, limit=1)
        if not conversation:
            pytest.skip('No conversations found in the database — cannot run integration tests')
        return conversation[0].id


# ---------------------------------------------------------------------------
# Unit Tests (no DB required)
# ---------------------------------------------------------------------------

class TestHistoryRetrievalUnit:
    """Unit tests for HistoryRetrievalService that don't require a database."""

    def test_input_model_creation(self):
        """HistoryRetrievalInput accepts a conversation_id string."""
        inp = HistoryRetrievalInput(conversation_id='test-conv-123')
        assert inp.conversation_id == 'test-conv-123'

    def test_output_model_defaults(self):
        """HistoryRetrievalOutput accepts empty memories and summary."""
        out = HistoryRetrievalOutput(conversation_memories=[], conversation_summary='')
        assert out.conversation_memories == []
        assert out.conversation_summary == ''

    def test_settings_model(self):
        """HistoryRetrievalSettings accepts n_turns."""
        settings = HistoryRetrievalSettings(n_turns=5)
        assert settings.n_turns == 5

    def test_qa_memory_pair_simplize(self):
        """QAMemoryPair.simplize() returns the expected role/content list."""
        from aqi_agent.shared.models.memory import Answer, Question
        pair = QAMemoryPair(
            qa_list=(
                Question(question='What is AQI?'),
                Answer(answer='Air Quality Index'),
            )
        )
        simplified = pair.simplize()
        assert len(simplified) == 2
        assert simplified[0]['role'] == 'user'
        assert simplified[0]['content'] == 'What is AQI?'
        assert simplified[1]['role'] == 'assistant'
        assert simplified[1]['content'] == 'Air Quality Index'


# ---------------------------------------------------------------------------
# Integration Tests (requires a running PostgreSQL database)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestHistoryRetrievalIntegration:
    """Integration tests that query a real PostgreSQL database."""

    @pytest.mark.asyncio
    async def test_process_with_valid_conversation_id(
        self, history_service, conversation_id,
    ):
        """process() returns memories and summary for a known conversation."""
        result = await history_service.process(
            HistoryRetrievalInput(conversation_id=conversation_id),
        )

        _log_output('test_process_with_valid_conversation_id', result)

        assert isinstance(result, HistoryRetrievalOutput)
        assert isinstance(result.conversation_summary, str)
        assert isinstance(result.conversation_memories, list)
        for mem in result.conversation_memories:
            assert isinstance(mem, QAMemoryPair)

    @pytest.mark.asyncio
    async def test_process_respects_n_turns(
        self, sql_database, conversation_id,
    ):
        """process() returns at most n_turns memories."""
        n_turns = 1
        service = HistoryRetrievalService(
            sql_database=sql_database,
            settings=HistoryRetrievalSettings(n_turns=n_turns),
        )
        result = await service.process(
            HistoryRetrievalInput(conversation_id=conversation_id),
        )

        _log_output('test_process_respects_n_turns', result)

        assert len(result.conversation_memories) <= n_turns

    @pytest.mark.asyncio
    async def test_process_with_nonexistent_conversation_id(
        self, history_service,
    ):
        """process() returns empty memories and summary for a fake conversation_id."""
        result = await history_service.process(
            HistoryRetrievalInput(conversation_id='nonexistent-conversation-id-999'),
        )

        _log_output('test_process_with_nonexistent_conversation_id', result)

        assert result.conversation_memories == []
        assert result.conversation_summary == ''

    @pytest.mark.asyncio
    async def test_process_with_empty_conversation_id(
        self, history_service,
    ):
        """process() handles an empty string gracefully."""
        result = await history_service.process(
            HistoryRetrievalInput(conversation_id=''),
        )

        _log_output('test_process_with_empty_conversation_id', result)

        assert result.conversation_memories == []
        assert result.conversation_summary == ''

    @pytest.mark.asyncio
    async def test_gprocess_with_valid_conversation_id(
        self, history_service, conversation_id,
    ):
        """gprocess() wraps results correctly into history_retrieval_state."""
        state = {'conversation_id': conversation_id}
        result = await history_service.gprocess(state)

        _log_gprocess_output('test_gprocess_with_valid_conversation_id', result)

        assert 'history_retrieval_state' in result
        hs = result['history_retrieval_state']
        assert 'conversation_summary' in hs
        assert 'conversation_memories' in hs
        assert isinstance(hs['conversation_memories'], list)

    @pytest.mark.asyncio
    async def test_gprocess_with_nonexistent_conversation_id(
        self, history_service,
    ):
        """gprocess() returns empty state for a fake conversation_id."""
        state = {'conversation_id': 'nonexistent-conversation-id-999'}
        result = await history_service.gprocess(state)

        _log_gprocess_output('test_gprocess_with_nonexistent_conversation_id', result)

        assert 'history_retrieval_state' in result
        hs = result['history_retrieval_state']
        assert hs['conversation_memories'] == []
        assert hs['conversation_summary'] == ''

    @pytest.mark.asyncio
    async def test_conversation_memories_structure(
        self, history_service, conversation_id,
    ):
        """Each memory returned has a valid qa_list with Question & Answer."""
        result = await history_service.process(
            HistoryRetrievalInput(conversation_id=conversation_id),
        )

        _log_output('test_conversation_memories_structure', result)

        for mem in result.conversation_memories:
            assert mem.qa_list is not None, 'qa_list should not be None'
            question, answer = mem.qa_list
            assert question.question, 'Question text should not be empty'
            assert isinstance(answer.answer, str), 'Answer should be a string'
