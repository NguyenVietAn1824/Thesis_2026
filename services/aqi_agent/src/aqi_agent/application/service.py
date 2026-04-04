from __future__ import annotations

from typing import Any
from typing import List
from typing import Literal

from base import BaseModel
from base import BaseService
from aqi_agent.domain.answer_generator import AnswerGeneratorService
from aqi_agent.domain.autocorrector import AutocorrectorService
from aqi_agent.domain.fixsql_agent import FixSQLService
from aqi_agent.domain.example_management import ExampleManagementService
from aqi_agent.domain.history_retrieval import HistoryRetrievalService
from aqi_agent.domain.human_intervent import HumanInterventService
from aqi_agent.domain.interrupt_checker import InterruptCheckerService
from aqi_agent.domain.memory_updater import MemoryUpdaterService
from aqi_agent.domain.planner import PlannerService
from aqi_agent.domain.rephrase_question import RephraseService
from aqi_agent.domain.sql_execution_handler import SQLExecutionHandlerService
from aqi_agent.domain.sql_generator import MatchSQLGeneratorService
from aqi_agent.domain.sql_generator import MismatchSQLGeneratorService
from aqi_agent.domain.sql_validator import SQLValidatorService
from aqi_agent.domain.table_pruner import TablePrunerService
from aqi_agent.shared.models.state import AnswerGeneratorState
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import FixSQLAgentState
from aqi_agent.shared.models.state import ExampleRetrievalState
from aqi_agent.shared.models.state import HistoryRetrievalState
from aqi_agent.shared.models.state import HumanInterventState
from aqi_agent.shared.models.state import PlannerServiceState
from aqi_agent.shared.models.state import RephraseServiceState
from aqi_agent.shared.models.state import SQLExecutionState
from aqi_agent.shared.models.state import SQLGeneratorState
from aqi_agent.shared.models.state import SQLValidatorState
from aqi_agent.shared.models.state import TablePrunerState
from aqi_agent.shared.resources import Resources
from easydict import EasyDict
from fastapi import BackgroundTasks
from fastapi.encoders import jsonable_encoder
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from langgraph.types import interrupt
from logger import get_logger

logger = get_logger(__name__)


class AQIAgentInput(BaseModel):
    question: str
    conversation_id: str
    user_id: str


class AQIAgentOutput(BaseModel):
    response: str


class AQIAgentApplication(BaseService):

    resources: Resources

    @property
    def interrupt_checker_service(self) -> InterruptCheckerService:
        return InterruptCheckerService(
            sql_database=self.resources.sql_database,
        )

    @property
    def rephrase_service(self) -> RephraseService:
        return RephraseService(
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.rephrase_question,
        )

    @property
    def history_retrieval_service(self) -> HistoryRetrievalService:
        return HistoryRetrievalService(
            sql_database=self.resources.sql_database,
            settings=self.resources.settings.history_retrieval,
        )

    @property
    def table_pruner_service(self) -> TablePrunerService:
        return TablePrunerService(
            opensearch_service=self.resources.opensearch_service,
            litellm_service=self.resources.litellm_service,
            table_pruner_settings=self.resources.settings.table_pruner,
        )

    @property
    def example_management_service(self) -> ExampleManagementService:
        return ExampleManagementService(
            opensearch_service=self.resources.opensearch_service,
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.example_management,
        )

    @property
    def planner_service(self) -> PlannerService:
        return PlannerService(
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.planner,
        )

    @property
    def human_intervent_service(self) -> HumanInterventService:
        return HumanInterventService(
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.human_intervent,
        )

    @property
    def autocorrector_service(self) -> AutocorrectorService:
        return AutocorrectorService(
            redis_client=self.resources.redis_client,
            settings=self.resources.settings.autocorrector,
        )

    @property
    def match_sql_generator_service(self) -> MatchSQLGeneratorService:
        return MatchSQLGeneratorService(
            litellm_service=self.resources.litellm_service,
            autocorrector_service=self.autocorrector_service,
            settings=self.resources.settings.match_sql_generator,
        )

    @property
    def mismatch_sql_generator_service(self) -> MismatchSQLGeneratorService:
        return MismatchSQLGeneratorService(
            litellm_service=self.resources.litellm_service,
            autocorrector_service=self.autocorrector_service,
            settings=self.resources.settings.mismatch_sql_generator,
        )

    @property
    def answer_generator_service(self) -> AnswerGeneratorService:
        return AnswerGeneratorService(
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.answer_generator,
        )

    @property
    def sql_validator_service(self) -> SQLValidatorService:
        return SQLValidatorService()

    @property
    def sql_execution_handler_service(self) -> SQLExecutionHandlerService:
        return SQLExecutionHandlerService(
            sql_database=self.resources.sql_database,
            settings=self.resources.settings.sql_execution,
        )

    @property
    def fixsql_agent_service(self) -> FixSQLService:
        return FixSQLService(
            litellm_service=self.resources.litellm_service,
            settings=self.resources.settings.fixsql_agent,
        )

    @property
    def memory_updater_service(self) -> MemoryUpdaterService:
        return MemoryUpdaterService(
            sql_database=self.resources.sql_database,
            settings=self.resources.settings.memory_updater,
            litellm_service=self.resources.litellm_service,
        )

    def join_nodes(self, state: ChatwithDBState) -> ChatwithDBState:
        """
        Join the outputs of parallel nodes (table_pruner, retrieve_example)
        back into the main state.
        """
        return state

    @property
    def nodes(self) -> EasyDict:
        return EasyDict(
            {
                'interrupt_checker': self.interrupt_checker_service.gprocess,
                'rephrase_question': self.rephrase_service.gprocess,
                'retrieve_history': self.history_retrieval_service.gprocess,
                'retrieve_example': self.example_management_service.gprocess,
                'table_pruner': self.table_pruner_service.gprocess,
                'planner': self.planner_service.gprocess,
                'match_sql_generator': self.match_sql_generator_service.gprocess,
                'answer_generator': self.answer_generator_service.gprocess,
                'join_nodes': self.join_nodes,
                'human_intervent': self.human_intervent_service.gprocess,
                'mismatch_sql_generator': self.mismatch_sql_generator_service.gprocess,
                'sql_validator': self.sql_validator_service.gprocess,
                'fixsql_agent': self.fixsql_agent_service.gprocess,
                'sql_execution_handler': self.sql_execution_handler_service.gprocess,
            },
        )

    async def check_interrupt_node(self, state: ChatwithDBState) -> ChatwithDBState:
        """
        Interrupt the graph when need_context is False,
        allowing human-in-the-loop confirmation before proceeding.
        """
        logger.info('Checking for interrupt', extra={'rephrased_state': state['interrupt']})
        interrupt(state)
        return {**state, 'interrupt': True}

    def _build_graph(self) -> Any:
        """
        Compile the state graph for the AQI Agent service.

        This graph defines the flow of states and transitions for air quality
        data querying using a text-to-SQL pipeline.

        Returns:
            Compiled state graph ready for invocation.
        """
        graph = StateGraph(
            ChatwithDBState,
        )
        for node, action in self.nodes.items():
            graph.add_node(node, action)

        def rephrase_question_route(
            state: ChatwithDBState,
        ) -> List[Literal['table_pruner', 'retrieve_example', 'human_intervent']]:
            if state.get('rephrased_state', {}).get('need_context', False):
                return ['table_pruner', 'retrieve_example']
            return ['human_intervent']

        def interrupt_router(
            state: ChatwithDBState,
        ) -> Literal['retrieve_history', 'end']:
            if not state.get('interrupt', False):
                return 'retrieve_history'
            return 'end'

        # START -> interrupt_checker
        graph.add_edge(START, 'interrupt_checker')

        # interrupt_checker -> retrieve_history | END
        graph.add_conditional_edges(
            'interrupt_checker',
            interrupt_router,
            {
                'retrieve_history': 'retrieve_history',
                'end': END,
            },
        )

        # retrieve_history -> rephrase_question
        graph.add_edge('retrieve_history', 'rephrase_question')

        # rephrase_question -> [table_pruner || retrieve_example] | human_intervent
        graph.add_conditional_edges(
            'rephrase_question',
            rephrase_question_route,
            {
                'table_pruner': 'table_pruner',
                'retrieve_example': 'retrieve_example',
                'human_intervent': 'human_intervent',
            },
        )

        # parallel nodes -> join_nodes
        graph.add_edge('retrieve_example', 'join_nodes')
        graph.add_edge('table_pruner', 'join_nodes')

        def generate_mode_route(state: ChatwithDBState) -> str:
            if state.get('example_retrieval_state', {}).get('examples', []):
                logger.info(
                    'Found %d examples, proceeding to Match and Generate pipeline.',
                    len(state.get('example_retrieval_state', {}).get('examples', [])),
                )
                return 'match_sql_generator'
            elif state.get('table_pruner_state', {}).get('pruned_schema', ''):
                logger.info('No examples found but pruned schema is available, proceeding to Think and Generate pipeline.')
                return 'planner'

            logger.warning('No examples and no pruned schema found, proceeding to human intervention for clarification.')
            return 'human_intervent'

        # join_nodes -> match_sql_generator | planner | human_intervent
        graph.add_conditional_edges(
            'join_nodes',
            generate_mode_route,
            {
                'match_sql_generator': 'match_sql_generator',
                'planner': 'planner',
                'human_intervent': 'human_intervent',
            },
        )

        # match_sql_generator -> sql_validator
        graph.add_edge('match_sql_generator', 'sql_validator')

        def planner_route(
            state: ChatwithDBState,
        ) -> Literal['mismatch_sql_generator', 'human_intervent']:
            if state.get('planner_state', {}).get('requires_clarification', False):
                return 'human_intervent'
            return 'mismatch_sql_generator'

        # planner -> mismatch_sql_generator | human_intervent
        graph.add_conditional_edges(
            'planner',
            planner_route,
            {
                'mismatch_sql_generator': 'mismatch_sql_generator',
                'human_intervent': 'human_intervent',
            },
        )

        # mismatch_sql_generator -> sql_validator
        graph.add_edge('mismatch_sql_generator', 'sql_validator')

        def route_sql_validator(
            state: ChatwithDBState,
        ) -> Literal['sql_execution_handler', 'human_intervent']:
            if state.get('sql_validator_state', {}).get('is_valid', False):
                return 'sql_execution_handler'
            return 'human_intervent'

        # sql_validator -> sql_execution_handler | human_intervent
        graph.add_conditional_edges(
            'sql_validator',
            route_sql_validator,
            {
                'sql_execution_handler': 'sql_execution_handler',
                'human_intervent': 'human_intervent',
            },
        )

        def route_sql_execution(
            state: ChatwithDBState,
        ) -> Literal['fixsql_agent', 'answer_generator', 'human_intervent']:
            sql_execution_state = state.get('sql_execution_state', {})

            # Check if max retries exceeded first
            if sql_execution_state.get('exceeded_max_retries', False):
                logger.warning('SQL fix retry limit exceeded. Navigating to human_intervent.')
                return 'human_intervent'

            if sql_execution_state.get('error_message', ''):
                return 'fixsql_agent'
            return 'answer_generator'

        # sql_execution_handler -> fixsql_agent | answer_generator | human_intervent
        graph.add_conditional_edges(
            'sql_execution_handler',
            route_sql_execution,
            {
                'fixsql_agent': 'fixsql_agent',
                'answer_generator': 'answer_generator',
                'human_intervent': 'human_intervent',
            },
        )

        # critic_agent loops back -> sql_validator
        graph.add_edge('fixsql_agent', 'sql_validator')

        # Terminal nodes
        graph.add_edge('answer_generator', END)
        graph.add_edge('human_intervent', END)

        return graph.compile()

    def __init_chatbot_state(self, inputs: AQIAgentInput) -> ChatwithDBState:
        """Initialize the chatbot state with input data.

        Creates a new ChatwithDBState instance populated with user input and default
        values for all state variables used throughout the AQI agent pipeline.

        Args:
            inputs: AQIAgentInput containing conversation ID, user ID, and question.

        Returns:
            ChatwithDBState: Initialized state object with all required fields.
        """
        return ChatwithDBState(
            question=inputs.question,
            conversation_id=inputs.conversation_id,
            interrupt=False,
            user_id=inputs.user_id,
            answer='',
            history_retrieval_state=HistoryRetrievalState(
                conversation_summary='',
                conversation_memories=[],
            ),
            rephrased_state=RephraseServiceState(
                rephrased_main_question='',
                need_context=False,
                language='',
            ),
            table_pruner_state=TablePrunerState(
                pruned_schema='',
                retrieved_tables=[],
                column_selection=[],
            ),
            example_retrieval_state=ExampleRetrievalState(
                examples=[],
            ),
            planner_state=PlannerServiceState(
                subtasks=[],
                requires_clarification=False,
                planning_summary='',
            ),
            sql_generator_state=SQLGeneratorState(
                sql_query='',
            ),
            human_intervent_state=HumanInterventState(
                answer='',
            ),
            sql_execution_state=SQLExecutionState(
                execution_result=None,
                error_message=None,
                number_of_rows=None,
                retry_count=0,
                exceeded_max_retries=False,
            ),
            fixsql_agent_state=FixSQLAgentState(
                error_explanation='',
                fixed_sql='',
                is_fixed=False,
            ),
            answer_generator_state=AnswerGeneratorState(
                answer='',
                able_to_answer=False,
            ),
            sql_validator_state=SQLValidatorState(
                is_valid=False,
                error_message=None,
                sanitized_query=None,
            ),
        )

    async def process(
        self,
        inputs: AQIAgentInput,
        background_tasks: BackgroundTasks,
    ) -> AQIAgentOutput:
        """
        Process the AQI agent application logic.

        Takes the user input, initializes the state, and invokes the compiled
        state graph. The graph processes the input through the text-to-SQL pipeline,
        ultimately producing a natural language response about air quality data.

        Args:
            inputs: AQIAgentInput containing the user's question and context.
            background_tasks: FastAPI BackgroundTasks for scheduling memory updates.

        Returns:
            AQIAgentOutput containing the agent's response.
        """
        chatwithdb_state: ChatwithDBState = self.__init_chatbot_state(
            inputs=inputs,
        )
        compiled_graph = self._build_graph()
        graph_output = await compiled_graph.ainvoke(
            jsonable_encoder(chatwithdb_state),
        )

        need_context = graph_output.get('rephrased_state', {}).get('need_context', False)
        requires_clarification = graph_output.get('planner_state', {}).get('requires_clarification', False)
        exceeded_max_retries = graph_output.get('sql_execution_state', {}).get('exceeded_max_retries', False)
        no_relevant_schema = (
            need_context
            and not graph_output.get('table_pruner_state', {}).get('pruned_schema', '')
            and not graph_output.get('example_retrieval_state', {}).get('examples', [])
        )

        if not need_context or requires_clarification or exceeded_max_retries or no_relevant_schema:
            response = graph_output.get('human_intervent_state', {}).get('answer', '')
        elif need_context:
            response = graph_output.get('answer_generator_state', {}).get('answer', '')
        else:
            response = graph_output.get('sql_execution_state', {}).get('execution_result', '')

        logger.info(
            "AQI Agent request processed",
            extra={
                "conversation_id": inputs.conversation_id,
                "user_id": inputs.user_id,
                "question": inputs.question,
                "response": response,
            },
        )
        background_tasks.add_task(
            self.memory_updater_service.gprocess,
            inputs=graph_output,
        )
        return AQIAgentOutput(response=response)
