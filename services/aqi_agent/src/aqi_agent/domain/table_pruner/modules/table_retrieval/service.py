from __future__ import annotations

from typing import Any

from base import BaseModel
from base import BaseService
from aqi_agent.shared.settings import TablePrunerSettings
from lite_llm import LiteLLMEmbeddingInput
from lite_llm import LiteLLMService
from logger import get_logger
from opensearch import OpenSearchInput
from opensearch import OpenSearchService

logger = get_logger(__name__)


class TableRetrievalInput(BaseModel):
    query: str


class TableRetrievalOutput(BaseModel):
    results: list[dict[str, Any]]


class TableRetrievalService(BaseService):
    opensearch_service: OpenSearchService
    litellm_service: LiteLLMService
    settings: TablePrunerSettings

    async def process(self, inputs: TableRetrievalInput) -> TableRetrievalOutput:
        """
        Main processing function for the TableRetrievalService. This function generates an embedding for the input query and performs a hybrid search over indexed table descriptions in OpenSearch to retrieve relevant tables.

        Args:
            inputs (TableRetrievalInput): The input data for the table retrieval process.

        Raises:
            e1: If embedding generation fails.
            e2: If table retrieval from OpenSearch fails.
        Returns:
            TableRetrievalOutput: The output data for the table retrieval process.
        """
        try:
            embedding = await self.litellm_service.embedding_async(
                inputs=LiteLLMEmbeddingInput(
                    input=inputs.query,
                    embedding_model=self.opensearch_service.settings.embedding_model,
                    encoding_format=self.opensearch_service.settings.encoding_format,
                    dimensions=self.opensearch_service.settings.dimensions,
                ),
            )
        except Exception as e1:
            logger.exception(
                'Failed to generate embedding for query',
                extra={
                    'query': inputs.query,
                    'error': str(e1),
                },
            )
            raise e1

        try:
            search_results = await self.opensearch_service.process(
                inputs=OpenSearchInput(
                    query_body={
                        '_source': {
                            'excludes': [
                                'embedding',
                            ],
                        },
                        'query': {
                            'hybrid': {
                                'queries': [
                                    {
                                        'match': {
                                            'text': inputs.query,
                                        },
                                    },
                                    {
                                        'knn': {
                                            'embedding': {
                                                'vector': embedding.vector,
                                                'k': self.settings.knn_size,
                                            },

                                        },
                                    },
                                ],
                            },
                        },
                    },
                    index_name=self.settings.index_name,
                    params={
                        'search_pipeline': self.settings.search_pipeline,
                    },
                ),
            )
            return TableRetrievalOutput(results=search_results.results)
        except Exception as e2:
            logger.exception(
                'Failed to retrieve tables from OpenSearch',
                extra={
                    'query': inputs.query,
                    'error': str(e2),
                },
            )
            raise e2
