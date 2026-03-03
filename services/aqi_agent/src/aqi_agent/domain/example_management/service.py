from __future__ import annotations

from typing import Any

from base import BaseService
from aqi_agent.shared.models import RetrievedExample
from aqi_agent.shared.models.state import ChatwithDBState
from aqi_agent.shared.models.state import ExampleRetrievalState
from aqi_agent.shared.settings import ExampleManagementSettings
from lite_llm import LiteLLMEmbeddingInput
from lite_llm import LiteLLMService
from logger import get_logger
from open_search import AddDocumentInput
from open_search import OpenSearchInput
from open_search import OpenSearchService

from .models import ExampleRetrievalInput
from .models import ExampleRetrievalOutput

logger = get_logger(__name__)


class ExampleManagementService(BaseService):
    litellm_service: LiteLLMService
    opensearch_service: OpenSearchService
    settings: ExampleManagementSettings

    def create_index(self) -> bool:
        try:
            index_name = self.settings.index_name
            if self.opensearch_service.index_exists(index_name):
                return True

            index_body = {
                'settings': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0,
                    'knn': True,
                },
                'mappings': {
                    'properties': {
                        'id': {'type': 'text'},
                        'text': {'type': 'text'},
                        'sql_query': {'type': 'text'},
                        'embedding': {
                            'type': 'knn_vector',
                            'dimension': self.settings.dimensions,
                            'method': {
                                'name': 'hnsw',
                                'space_type': 'cosinesimil',
                                'engine': 'faiss',
                            },
                        },
                    },
                },
            }
            return self.opensearch_service.create_index(index_name, index_body)
        except Exception as e:
            logger.exception(
                'Failed to create index for examples',
                extra={'error': str(e), 'index_name': self.settings.index_name},
            )
            raise

    async def index_examples(self, examples: list[dict]) -> bool:
        try:
            if not examples:
                logger.warning('No examples provided for indexing')
                return False

            documents: list[AddDocumentInput] = []
            for example in examples:
                try:
                    embedding = await self.litellm_service.embedding_async(
                        inputs=LiteLLMEmbeddingInput(
                            input=example['question'],
                            embedding_model=self.settings.embedding_model,
                            encoding_format=self.settings.encoding_format,
                            dimensions=self.settings.dimensions,
                        ),
                    )
                    documents.append(
                        AddDocumentInput(
                            text=example['question'],
                            embedding=embedding.vector,
                            metadata={'sql_query': example['sql_query']},
                        ),
                    )
                except Exception as e:
                    logger.exception(
                        'Error generating embedding for example',
                        extra={'error': str(e), 'example': example},
                    )
                    continue

            return self.opensearch_service.add_documents(
                documents=documents,
                index_name=self.settings.index_name,
            )
        except Exception as e:
            logger.exception(
                'Failed to index examples into OpenSearch',
                extra={'error': str(e)},
            )
            return False

    async def _build_search_query(self, query_text: str) -> dict[str, Any]:
        try:
            embedding = await self.litellm_service.embedding_async(
                inputs=LiteLLMEmbeddingInput(
                    input=query_text,
                    embedding_model=self.settings.embedding_model,
                    encoding_format=self.settings.encoding_format,
                    dimensions=self.settings.dimensions,
                ),
            )
            return {
                '_source': {'excludes': ['embedding']},
                'query': {
                    'knn': {
                        'embedding': {
                            'vector': embedding.vector,
                            'k': self.settings.knn_size,
                        },
                    },
                },
            }
        except Exception:
            logger.exception(
                'Failed to build search query for OpenSearch',
                extra={'query_text': query_text},
            )
            raise

    async def process(self, inputs: ExampleRetrievalInput) -> ExampleRetrievalOutput:
        try:
            search_query = await self._build_search_query(inputs.question)
            search_input = OpenSearchInput(
                index_name=self.settings.index_name,
                query_body=search_query,
                params={'size': self.settings.knn_size},
            )
            search_output = await self.opensearch_service.process(search_input)
        except Exception as e:
            logger.exception(
                'Error during example retrieval from OpenSearch',
                extra={'error': str(e), 'question': inputs.question},
            )
            raise

        try:
            examples = []
            for hit in search_output.results:
                source = hit.get('_source', {})
                if hit.get('_score', 1.0) < self.settings.threshold:
                    continue
                examples.append(
                    RetrievedExample(
                        id=hit.get('_id', ''),
                        question=source.get('text', ''),
                        sql_query=source.get('metadata', {}).get('sql_query', ''),
                        score=hit.get('_score', 0.0),
                    ),
                )
            return ExampleRetrievalOutput(examples=examples)
        except Exception:
            logger.exception(
                'Error processing search results from OpenSearch',
                extra={'search_output': search_output},
            )
            raise

    async def gprocess(self, inputs: ChatwithDBState) -> dict:
        try:
            output = await self.process(
                ExampleRetrievalInput(
                    question=inputs.get('rephrased_state', {}).get('rephrased_main_question', ''),
                ),
            )
            return {
                'example_retrieval_state': ExampleRetrievalState(
                    examples=[example.model_dump() for example in output.examples],
                ),
            }
        except Exception as e:
            logger.exception(
                'Example retrieval processing error',
                extra={
                    'error': str(e),
                    'rephrased_question': inputs.get('rephrased_question', ''),
                },
            )
            return {
                'example_retrieval_state': ExampleRetrievalState(examples=[]),
            }
