from __future__ import annotations

from typing_extensions import TypedDict


class RephraseServiceState(TypedDict):
    """
    TypedDict representing the state of the RephraseService processing.
    This dictionary holds various attributes related to the chatbot's
    interaction with the user, including questions, answers, user info,
    conversation details, and memory data.
    """
    rephrased_main_question: str
    need_context: bool
    language: str


class HistoryRetrievalState(TypedDict):
    """
    TypedDict representing the state of the HistoryRetrievalService processing.
    This dictionary holds various attributes related to the chatbot's
    interaction with the user, including questions, answers, user info,
    conversation details, and memory data.
    Attributes:
        conversation_memories: A list of QAMemoryPair objects representing recent conversation turns.
        conversation_summary: A string summarizing the conversation history.
    """
    conversation_summary: str
    conversation_memories: list[dict]


class TablePrunerState(TypedDict):
    """
    TypedDict representing the state of the TablePrunerService processing.
    This dictionary holds various attributes related to the chatbot's
    interaction with the user, including questions, answers, user info,
    conversation details, and memory data.
    Attributes:
        pruned_tables: A list of strings representing the names of tables that have been pruned.
    """
    pruned_schema: str
    retrieved_tables: list[dict]
    column_selection: list[dict]


class ExampleRetrievalState(TypedDict):
    """
    TypedDict representing the state of the ExampleRetrievalService processing.
    This dictionary holds various attributes related to the chatbot's
    interaction with the user, including questions, answers, user info,
    conversation details, and memory data.
    Attributes:
        examples: A list of RetrievedExample objects representing retrieved examples relevant to the user's question.
    """
    examples: list[dict]


class SubTask(TypedDict):
    """
    TypedDict representing a single subtask in a decomposed query plan.

    Attributes:
        task_id: Unique identifier for the subtask.
        description: Clear description of what this subtask accomplishes.
        depends_on: List of task_ids that must be completed before this task.
        sql_hint: Optional hint about the SQL operation needed.
    """
    task_id: str
    description: str
    depends_on: list[str]
    sql_hint: str


class PlannerServiceState(TypedDict):
    """
    TypedDict representing the state of the PlannerService processing.

    This dictionary holds the output of the planning agent including
    decomposed subtasks for SQL generation.

    Attributes:
        subtasks: List of ordered subtasks decomposed from the user query.
        requires_clarification: Whether the query requires human clarification before proceeding.
        planning_summary: A brief summary of the planning analysis.
    """
    subtasks: list[SubTask]
    requires_clarification: bool
    planning_summary: str


class HumanInterventState(TypedDict):
    """
    TypedDict representing the state of the HumanInterventService processing.
    This dictionary holds the answer generated when database context is not needed.
    Attributes:
        answer: The generated natural language response to the user.
    """
    answer: str


class SQLGeneratorState(TypedDict):
    """
    TypedDict representing the state of the SQLGeneratorService processing.

    This dictionary holds the output of the SQL generator including
    the generated SQL query and explanation.

    Attributes:
        sql_query: The generated SQL query.
    """
    sql_query: str


class SQLExecutionState(TypedDict):
    """
    TypedDict representing the state of the SQLExecutionHandlerService processing.
    Attributes:
        execution_result: The result of the SQL execution if successful.
        error_message: Error message if the SQL execution failed.
        number_of_rows: Number of rows returned by the SQL execution, if applicable.
        retry_count: Counter for SQL fix retry attempts.
        exceeded_max_retries: Flag indicating if max retries has been exceeded.
    """
    execution_result: str | None
    error_message: str | None
    number_of_rows: int | None
    retry_count: int
    exceeded_max_retries: bool


class FixSQLAgentState(TypedDict):
    error_explanation: str
    fixed_sql: str
    is_fixed: bool


class AnswerGeneratorState(TypedDict):
    answer: str
    able_to_answer: bool


class SQLValidatorState(TypedDict):
    is_valid: bool
    error_message: str | None
    sanitized_query: str | None


class ChatwithDBState(TypedDict):
    """
    TypedDict representing the state of the AQI Agent processing.
    This dictionary holds various attributes related to the agent's
    interaction with the user, including questions, answers, user info,
    conversation details, and memory data.
    """

    question: str
    conversation_id: str
    user_id: str
    interrupt: bool
    answer: str

    history_retrieval_state: HistoryRetrievalState
    rephrased_state: RephraseServiceState
    table_pruner_state: TablePrunerState
    example_retrieval_state: ExampleRetrievalState
    planner_state: PlannerServiceState
    sql_generator_state: SQLGeneratorState
    human_intervent_state: HumanInterventState
    sql_execution_state: SQLExecutionState
    fixsql_agent_state: FixSQLAgentState
    answer_generator_state: AnswerGeneratorState
    sql_validator_state: SQLValidatorState


class SubAgentState(TypedDict):
    
    task_id: str
    question: str
    description: str
    table_name: str