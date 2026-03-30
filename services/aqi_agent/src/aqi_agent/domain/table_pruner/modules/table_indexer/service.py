from __future__ import annotations

import asyncio
from typing import Any

from base import BaseModel
from base import BaseService
from aqi_agent.shared.settings.table_pruner import TablePrunerSettings
from lite_llm import LiteLLMEmbeddingInput
from lite_llm import LiteLLMService
from logger import get_logger
from opensearch import AddDocumentInput
from opensearch import OpenSearchService

logger = get_logger(__name__)


class TableIndexerInput(BaseModel):
    index_body: dict[str, Any]
    search_pipeline_body: dict[str, Any]
    mdl: dict[str, Any]


class TableIndexerOutput(BaseModel):
    success: bool


class TableIndexerService(BaseService):
    """Indexes table descriptions into OpenSearch for hybrid search"""
    opensearch_service: OpenSearchService
    litellm_service: LiteLLMService
    settings: TablePrunerSettings

    def create_search_pipeline(self, pipeline_id: str, pipeline_body: dict[str, Any]) -> bool:
        """
        Create OpenSearch search pipeline for table retrieval. This pipeline will be used to perform hybrid search over indexed table descriptions.

        Args:
            pipeline_id (str): The ID of the search pipeline to create.
            pipeline_body (dict[str, Any]): The body of the search pipeline configuration.

        Raises:
            e: If the search pipeline creation fails.

        Returns:
            bool: True if the search pipeline was created successfully, False otherwise.
        """
        try:
            result = self.opensearch_service.create_search_pipeline(
                pipeline_id=pipeline_id,
                pipeline_body=pipeline_body,
            )
            if not result:
                logger.warning(f'OpenSearch search pipeline already exists: {pipeline_id}')
            logger.info(f'Created OpenSearch search pipeline: {pipeline_id}')

            return result
        except Exception as e:
            logger.exception(
                'Failed to create OpenSearch search pipeline',
                extra={
                    'pipeline_id': pipeline_id,
                    'pipeline_body': pipeline_body,
                },
            )
            raise e

    def create_index(self, index_name: str, index_body: dict[str, Any]) -> bool:
        """
        Create OpenSearch index for storing table descriptions and embeddings.

        Args:
            index_name (str): The name of the OpenSearch index to create.
            index_body (dict[str, Any]): The body of the index configuration.

        Raises:
            e: If the index creation fails.

        Returns:
            bool: True if the index was created successfully, False if it already exists or creation failed.
        """
        try:
            result = self.opensearch_service.create_index(
                index_name=index_name,
                index_body=index_body,
            )
            if not result:
                logger.warning(f'OpenSearch index already exists: {index_name}')
            logger.info(f'Created OpenSearch index: {index_name}')

            return result
        except Exception as e:
            logger.exception(
                'Failed to create OpenSearch index',
                extra={
                    'index_name': index_name,
                    'index_body': index_body,
                },
            )
            raise e

    async def index_tables(self, mdl: dict) -> bool:
        """
        Index table descriptions and embeddings into OpenSearch. For each table in the MDL, generate an embedding for its description and index it along with metadata about the table.

        Args:
            mdl (dict): The MDL containing table models to be indexed.

        Raises:
            e: If embedding generation or indexing fails.

        Returns:
            bool: True if the tables were indexed successfully, False otherwise.
        """
        documents: list[AddDocumentInput] = []
        for i, model in enumerate(mdl['models']):
            try:
                if i > 0:
                    await asyncio.sleep(3)  # Rate limit protection
                text = model['properties']['description']
                embedding_output = await self.litellm_service.embedding_async(
                    inputs=LiteLLMEmbeddingInput(
                        input=text,
                        embedding_model=self.opensearch_service.settings.embedding_model,
                        encoding_format=self.opensearch_service.settings.encoding_format,
                        dimensions=self.opensearch_service.settings.dimensions,
                    ),
                )
                documents.append(
                    AddDocumentInput(
                        text=text,
                        embedding=embedding_output.vector,
                        metadata={
                            'table_name': model['name'],
                            'columns': model['columns'],
                        },
                    ),
                )
            except Exception as e:
                logger.warning(
                    'Failed to generate embedding for table description',
                    extra={
                        'table_model': model,
                        'error': str(e),
                    },
                )

        if not documents:
            logger.warning('No documents to index into OpenSearch')
            return False

        try:
            result = self.opensearch_service.add_documents(
                documents=documents,
                index_name=self.settings.index_name,
            )
            if not result:
                logger.warning('Documents indexing was not successful')
            logger.info(f'Indexed {len(documents)} table descriptions into OpenSearch')

            return result
        except Exception as e:
            logger.exception(
                'Failed to index table descriptions into OpenSearch',
                extra={
                    'documents': documents,
                    'index_name': self.settings.index_name,
                },
            )
            raise e

    async def process(self, inputs: TableIndexerInput) -> TableIndexerOutput:
        """
        Main processing function for the TableIndexerService. This function orchestrates the creation of the OpenSearch index, indexing of table descriptions, and creation of the search pipeline.

        Args:
            inputs (TableIndexerInput): The input data for the table indexing process.

        Returns:
            TableIndexerOutput: The output data for the table indexing process.
        """
        _ = self.create_index(
            index_name=self.settings.index_name,
            index_body=inputs.index_body,
        )

        index_tables_result = await self.index_tables(
            mdl=inputs.mdl,
        )

        _ = self.create_search_pipeline(
            pipeline_id=self.settings.search_pipeline,
            pipeline_body=inputs.search_pipeline_body,
        )

        return TableIndexerOutput(success=index_tables_result)
