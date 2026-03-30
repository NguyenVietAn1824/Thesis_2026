from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from lite_llm import LiteLLMService, LiteLLMSetting
from opensearch import OpenSearchService, OpenSearchSettings
from aqi_agent.domain.table_pruner.service import TablePrunerService, TablePrunerInput
from aqi_agent.shared.settings.table_pruner import TablePrunerSettings

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

async def main():
    litellm_service = LiteLLMService(settings=LiteLLMSetting(
        url=os.getenv('LITELLM__URL', 'http://localhost:9510'),
        token=os.getenv('LITELLM__TOKEN', ''),
        model=os.getenv('LITELLM__MODEL', 'gpt-4o-mini'),
        embedding_model=os.getenv('LITELLM__EMBEDDING_MODEL', 'text-embedding-3-small'),
        dimensions=int(os.getenv('LITELLM__DIMENSIONS', '1536')),
    ))

    opensearch_service = OpenSearchService(settings=OpenSearchSettings(
        host=os.getenv('OPENSEARCH__HOST', 'localhost'),
        port=int(os.getenv('OPENSEARCH__PORT', '19200')),
        knn_size=3,
        embedding_model=os.getenv('LITELLM__EMBEDDING_MODEL', 'text-embedding-3-small'),
        dimensions=int(os.getenv('LITELLM__DIMENSIONS', '1536')),
    ))

    table_pruner_settings = TablePrunerSettings(
        index_name=os.getenv('TABLE_PRUNER__INDEX_NAME', 'aqi-tables'),
        search_pipeline=os.getenv('TABLE_PRUNER__SEARCH_PIPELINE', 'table-retrieval-pipeline'),
        knn_size=3,
        model=os.getenv('LITELLM__MODEL', 'gpt-4o-mini'),
    )

    pruner = TablePrunerService(
        opensearch_service=opensearch_service,
        litellm_service=litellm_service,
        table_pruner_settings=table_pruner_settings,
    )

    queries = [
        "Chỉ số ô nhiễm PM2.5 ở quận Cầu Giấy hôm nay là bao nhiêu?",
        "Cho mình xem danh sách các tỉnh thành ở Việt Nam.",
        "Tra cứu mã của phường Tràng Tiền"
    ]

    for question in queries:
        print(f"\n=========================================")
        print(f"QUERY: {question}")
        print(f"=========================================")
        
        result = await pruner.process(inputs=TablePrunerInput(question=question))
        
        print("\n[RETRIEVED TABLES]")
        for table in result.retrieved_tables:
            # Depending on OpenSearch schema, table details might be in _source or metadata
            table_name = table.get('_source', {}).get('metadata', {}).get('table_name', 'Unknown')
            print(f" - {table_name}")
            
        print("\n[PRUNED COLUMN SELECTION]")
        for selection in result.column_selection.results:
            print(f" - Table: {selection.table_name}")
            print(f"   Selected Columns: {selection.selected_columns}")
            print(f"   Reasoning: {selection.reasoning}")

if __name__ == '__main__':
    asyncio.run(main())
