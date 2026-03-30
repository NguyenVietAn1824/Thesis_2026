from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from lite_llm import LiteLLMService
from lite_llm import LiteLLMSetting
from opensearch import OpenSearchService
from opensearch import OpenSearchSettings
from aqi_agent.domain.table_pruner.service import TableIndexerInput
from aqi_agent.domain.table_pruner.service import TableIndexerService
from aqi_agent.shared.settings.table_pruner import TablePrunerSettings

# Load .env from project root (script/ -> ../.env)
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Index AQI tables into OpenSearch for table pruner',
    )
    parser.add_argument(
        '--index-name',
        type=str,
        default=os.getenv('TABLE_PRUNER__INDEX_NAME', 'aqi-tables'),
        help='OpenSearch index name (default: aqi-tables)',
    )
    parser.add_argument(
        '--search-pipeline',
        type=str,
        default=os.getenv('TABLE_PRUNER__SEARCH_PIPELINE', 'table-retrieval-pipeline'),
        help='OpenSearch search pipeline name (default: table-retrieval-pipeline)',
    )
    parser.add_argument(
        '--knn-size',
        type=int,
        default=int(os.getenv('TABLE_PRUNER__KNN_SIZE', '5')),
        help='Number of nearest neighbors to retrieve (default: 5)',
    )
    parser.add_argument(
        '--model',
        type=str,
        default=os.getenv('LITELLM__MODEL', 'gpt-4o-mini'),
        help='LLM model name used by table pruner (default: gpt-4o-mini)',
    )
    parser.add_argument(
        '--max-completion-tokens',
        type=int,
        default=int(os.getenv('LITELLM__MAX_COMPLETION_TOKENS', '2048')),
        help='Maximum completion tokens for the model (default: 2048)',
    )
    parser.add_argument(
        '--mdl-path',
        type=str,
        default=None,
        help='Path to the MDL JSON file (default: <project_root>/mdl.json)',
    )
    parser.add_argument(
        '--dimensions',
        type=int,
        default=int(os.getenv('LITELLM__DIMENSIONS', '1536')),
        help='Embedding vector dimensions (default: 1536)',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Force re-index by deleting the existing index and search pipeline first',
    )
    return parser.parse_args()


async def main(args: argparse.Namespace) -> None:
    # ── LiteLLM ──────────────────────────────────────────────────────────────
    llm_setting = LiteLLMSetting(
        url=os.getenv('LITELLM__URL', 'http://localhost:9510'),
        token=os.getenv('LITELLM__TOKEN', ''),
        model=os.getenv('LITELLM__MODEL', 'gpt-4o-mini'),
        embedding_model=os.getenv('LITELLM__EMBEDDING_MODEL', 'text-embedding-3-small'),
        frequency_penalty=int(os.getenv('LITELLM__FREQUENCY_PENALTY', '0')),
        n=int(os.getenv('LITELLM__N', '1')),
        presence_penalty=int(os.getenv('LITELLM__PRESENCE_PENALTY', '0')),
        temperature=int(os.getenv('LITELLM__TEMPERATURE', '0')),
        top_p=int(os.getenv('LITELLM__TOP_P', '1')),
        max_completion_tokens=int(os.getenv('LITELLM__MAX_COMPLETION_TOKENS', '4096')),
        encoding_format=os.getenv('LITELLM__ENCODING_FORMAT', 'float'),
        dimensions=args.dimensions,
        max_length=int(os.getenv('LITELLM__MAX_LENGTH', '8191')),
        timeout=int(os.getenv('LITELLM__TIMEOUT', '60')),
        connect_timeout=int(os.getenv('LITELLM__CONNECT_TIMEOUT', '10')),
        max_connections=int(os.getenv('LITELLM__MAX_CONNECTIONS', '200')),
        max_keepalive_connections=int(os.getenv('LITELLM__MAX_KEEPALIVE_CONNECTIONS', '40')),
        context_window=int(os.getenv('LITELLM__CONTEXT_WINDOW', '100000')),
        condition_model=os.getenv('LITELLM__CONDITION_MODEL', 'gpt-4o-mini'),
    )
    litellm_service = LiteLLMService(settings=llm_setting)

    # ── OpenSearch ────────────────────────────────────────────────────────────
    opensearch_settings = OpenSearchSettings(
        host=os.getenv('OPENSEARCH__HOST', 'localhost'),
        port=int(os.getenv('OPENSEARCH__PORT', '19200')),
        knn_size=args.knn_size,
        embedding_model=os.getenv('LITELLM__EMBEDDING_MODEL', 'text-embedding-3-small'),
        encoding_format=os.getenv('LITELLM__ENCODING_FORMAT', 'float'),
        dimensions=args.dimensions,
    )
    opensearch_service = OpenSearchService(settings=opensearch_settings)

    # ── TablePruner ───────────────────────────────────────────────────────────
    table_pruner_settings = TablePrunerSettings(
        index_name=args.index_name,
        search_pipeline=args.search_pipeline,
        knn_size=args.knn_size,
        model=args.model,
        max_completion_tokens=args.max_completion_tokens,
    )

    table_indexer = TableIndexerService(
        litellm_service=litellm_service,
        opensearch_service=opensearch_service,
        settings=table_pruner_settings,
    )

    # ── Force delete old index & pipeline if requested ─────────────────────
    if args.force:
        print('\n🗑️  --force: Deleting existing index and search pipeline...')
        if opensearch_service.index_exists(index_name=table_pruner_settings.index_name):
            deleted = opensearch_service.delete_index(index_name=table_pruner_settings.index_name)
            print(f'   Index "{table_pruner_settings.index_name}": {"deleted" if deleted else "failed to delete"}')
        else:
            print(f'   Index "{table_pruner_settings.index_name}": does not exist (skip)')
        if opensearch_service.search_pipeline_exists(pipeline_id=table_pruner_settings.search_pipeline):
            deleted = opensearch_service.delete_search_pipeline(pipeline_id=table_pruner_settings.search_pipeline)
            print(f'   Pipeline "{table_pruner_settings.search_pipeline}": {"deleted" if deleted else "failed to delete"}')
        else:
            print(f'   Pipeline "{table_pruner_settings.search_pipeline}": does not exist (skip)')

    # ── Load MDL ──────────────────────────────────────────────────────────────
    if args.mdl_path:
        mdl_path = Path(args.mdl_path)
    else:
        mdl_path = Path(__file__).resolve().parent.parent / 'mdl.json'

    if not mdl_path.exists():
        print(f'❌ MDL file not found: {mdl_path}')
        raise FileNotFoundError(f'MDL file not found: {mdl_path}')

    with open(mdl_path) as f:
        mdl = json.load(f)

    print(f'📄 Loaded MDL from: {mdl_path}')
    print(f'📊 Models found   : {[m["name"] for m in mdl["models"]]}')

    # ── Build index body & search pipeline body ───────────────────────────────
    index_body = {
        'settings': {'index.knn': True},
        'mappings': {
            'properties': {
                'text': {'type': 'text'},
                'embedding': {
                    'type': 'knn_vector',
                    'dimension': args.dimensions,
                    'method': {
                        'name': 'hnsw',
                        'space_type': 'cosinesimil',
                        'engine': 'lucene',
                    },
                },
            },
        },
    }

    search_pipeline_body = {
        'description': 'Hybrid search pipeline for table pruner',
        'phase_results_processors': [
            {
                'normalization-processor': {
                    'normalization': {'technique': 'min_max'},
                    'combination': {
                        'technique': 'arithmetic_mean',
                        'parameters': {'weights': [0.3, 0.7]},
                    },
                },
            },
        ],
    }

    # ── Run via process() ─────────────────────────────────────────────────────
    print(f'\n📥 Indexing {len(mdl["models"])} table(s) into OpenSearch...')
    output = await table_indexer.process(
        inputs=TableIndexerInput(
            index_body=index_body,
            search_pipeline_body=search_pipeline_body,
            mdl=mdl,
        ),
    )

    if output.success:
        print('✅ Table indexing completed successfully!')
    else:
        print('⚠️  Table indexing finished with warnings — check logs for details.')


if __name__ == '__main__':
    asyncio.run(main(parse_args()))
