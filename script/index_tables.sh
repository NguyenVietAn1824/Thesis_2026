#!/usr/bin/env bash
# =============================================================================
# index_tables.sh — Index AQI tables into OpenSearch for the table pruner
#
# Usage:
#   ./script/index_tables.sh [OPTIONS]
#
# Options (all optional — defaults read from .env or built-in fallbacks):
#   --index-name NAME           OpenSearch index name          (default: aqi-tables)
#   --search-pipeline NAME      Search pipeline name           (default: table-retrieval-pipeline)
#   --knn-size N                Number of nearest neighbours   (default: 5)
#   --model MODEL               LLM model name                 (default: gpt-4.1-nano)
#   --max-completion-tokens N   Max completion tokens          (default: 2048)
#   --mdl-path PATH             Path to mdl.json               (default: auto-detected)
#   --dimensions N              Embedding vector dimensions    (default: 1536)
#   --force                     Delete existing index & pipeline before re-indexing
#
# Examples:
#   # Run with all defaults
#   ./script/index_tables.sh
#
#   # Override index name and model
#   ./script/index_tables.sh --index-name my-index --model gpt-4o-mini
#
#   # Use a custom MDL file
#   ./script/index_tables.sh --mdl-path /path/to/my_mdl.json
# =============================================================================

set -euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Load .env if it exists ────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
fi

# ── Defaults (can be overridden by .env or CLI args) ─────────────────────────
INDEX_NAME="${TABLE_PRUNER__INDEX_NAME:-aqi-tables}"
SEARCH_PIPELINE="${TABLE_PRUNER__SEARCH_PIPELINE:-table-retrieval-pipeline}"
KNN_SIZE="${TABLE_PRUNER__KNN_SIZE:-5}"
MODEL="${LITELLM__MODEL:-gpt-4.1-nano}"
MAX_COMPLETION_TOKENS="${LITELLM__MAX_COMPLETION_TOKENS:-2048}"
MDL_PATH=""
DIMENSIONS="${LITELLM__DIMENSIONS:-1536}"
FORCE=""

# ── Parse CLI arguments ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --index-name)
      INDEX_NAME="$2"
      shift 2
      ;;
    --search-pipeline)
      SEARCH_PIPELINE="$2"
      shift 2
      ;;
    --knn-size)
      KNN_SIZE="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --max-completion-tokens)
      MAX_COMPLETION_TOKENS="$2"
      shift 2
      ;;
    --mdl-path)
      MDL_PATH="$2"
      shift 2
      ;;
    --dimensions)
      DIMENSIONS="$2"
      shift 2
      ;;
    --force)
      FORCE="--force"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--index-name NAME] [--search-pipeline NAME] [--knn-size N] [--model NAME] [--max-completion-tokens N] [--mdl-path PATH] [--dimensions N]"
      exit 1
      ;;
  esac
done

echo "========================================================================"
echo "📥 INDEX TABLES — AQI Agent"
echo "========================================================================"
echo "📁 Project root      : $PROJECT_ROOT"
echo "� Index name        : $INDEX_NAME"
echo "🔍 Search pipeline   : $SEARCH_PIPELINE"
echo "🔢 KNN size          : $KNN_SIZE"
echo "🤖 Model             : $MODEL"
echo "🔑 Max tokens        : $MAX_COMPLETION_TOKENS"
echo "📐 Dimensions        : $DIMENSIONS"
[ -n "$MDL_PATH" ] && echo "📄 MDL path          : $MDL_PATH"
[ -n "$FORCE" ] && echo "🗑️  Force re-index   : YES"
echo "========================================================================"

# ── Build extra args ──────────────────────────────────────────────────────────
EXTRA_ARGS=""
[ -n "$MDL_PATH" ] && EXTRA_ARGS="--mdl-path $MDL_PATH"
[ -n "$FORCE" ] && EXTRA_ARGS="$EXTRA_ARGS --force"

# ── Run the indexer ───────────────────────────────────────────────────────────
uv run --package aqi-agent "$SCRIPT_DIR/index_tables.py" \
  --index-name "$INDEX_NAME" \
  --search-pipeline "$SEARCH_PIPELINE" \
  --knn-size "$KNN_SIZE" \
  --model "$MODEL" \
  --max-completion-tokens "$MAX_COMPLETION_TOKENS" \
  --dimensions "$DIMENSIONS" \
  $EXTRA_ARGS

EXIT_CODE=$?
echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Done!"
else
    echo "❌ index_tables.py exited with code $EXIT_CODE"
fi
echo "========================================================================"

exit $EXIT_CODE
