from __future__ import annotations

import unicodedata

import sqlglot
from base import BaseService
from aqi_agent.shared.settings import AutocorrectorSettings
from logger import get_logger
from rapidfuzz import fuzz
from rapidfuzz import process
from redis import Redis  # type: ignore[import-untyped]
from sqlglot import exp
from sqlglot.errors import ParseError

from .models import AutocorrectorInput
from .models import AutocorrectorOutput

logger = get_logger(__name__)


class FuzzyCorrectorService(BaseService):
    """Service for fuzzy correction of SQL WHERE clause values using Redis cache.

    This service performs fuzzy matching on WHERE column = 'value' conditions
    and replaces them with WHERE column IN (...) when matches exceed threshold.
    """

    redis_client: Redis
    settings: AutocorrectorSettings

    def _remove_accents(self, input_str: str) -> str:
        """Remove accents from input text for fuzzy matching normalization.

        Args:
            input_str: Input string.

        Returns:
            Input string with accents removed, or original string if normalization fails.
        """
        try:
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        except Exception:
            logger.warning(
                'Failed to remove accents from input string, using original string.',
                extra={'input_str': input_str},
            )
            return input_str

    def _extract_table_mapping(self, expression: exp.Expression) -> dict[str, str]:
        """Extract table and alias mapping from FROM/JOIN clauses.

        Args:
            expression: A sqlglot Expression representing the parsed SQL query.

        Returns:
            Dict mapping alias (and real name) to real table name.
            Example: ``FROM city c`` -> ``{'c': 'city', 'city': 'city'}``
        """
        try:
            mapping: dict[str, str] = {}
            for table in expression.find_all(exp.Table):
                real_name = table.name
                alias = table.alias or real_name
                if real_name:
                    mapping[alias] = real_name
                    if real_name not in mapping:
                        mapping[real_name] = real_name
            return mapping
        except Exception:
            logger.exception(
                'Failed to extract table mapping from SQL expression.',
                extra={'expression': expression.sql() if expression else None},
            )
            raise

    def _get_column_name(self, column: exp.Column, table_mapping: dict[str, str]) -> str:
        """Extract the full column name from a sqlglot Column node, resolved to real table name.

        Args:
            column: A sqlglot Column expression.
            table_mapping: Dict mapping alias/tables from ``_extract_table_mapping``.

        Returns:
            Full column name in the format ``table_name.column_name``.
        """
        try:
            table_alias = column.table
            column_name = column.name

            real_table_name = None
            if table_alias:
                real_table_name = table_mapping.get(table_alias, table_alias)
            elif table_mapping:
                real_table_name = list(table_mapping.values())[0]

            if real_table_name and column_name:
                return f'{real_table_name}.{column_name}'

            return column_name or ''
        except Exception:
            logger.exception(
                'Failed to get column name from SQL expression.',
                extra={'column': column.sql() if column else None},
            )
            raise

    def _find_cached_values_for_column(self, column_name: str) -> dict[str, list[str]]:
        """Retrieve cached frequent values for a specific column from Redis.

        Args:
            column_name: The column name in format ``table_name.column_name``.

        Returns:
            Dict mapping Redis keys to lists of cached values. Empty dict if none found.

        Raises:
            Exception: If Redis lookup fails.
        """
        try:
            pattern = f'{self.settings.redis_key_prefix}:{column_name}'
            matched_keys = []

            for key in self.redis_client.scan_iter(match=pattern, count=100):
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                matched_keys.append(key)

            result = {}
            for key in matched_keys:
                values = self.redis_client.lrange(key, 0, -1)
                decoded_values = [
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for v in values
                ]
                if decoded_values:
                    result[key] = decoded_values

            return result
        except Exception:
            logger.exception(
                'Failed to find cached values for column.',
                extra={'column_name': column_name},
            )
            raise

    def _fuzzy_match(
        self,
        query_value: str,
        cached_values: list[str],
        threshold: int,
        min_len_ratio: float | None,
        max_matches: int | None,
    ) -> list[str]:
        """Perform fuzzy matching of a query value against a list of cached values.

        Args:
            query_value: The value to match.
            cached_values: List of candidate values from cache.
            threshold: Minimum similarity score (0-100) to include a match.
            min_len_ratio: Minimum length ratio (0-1) for fuzzy match validity.
                Protects against substring false positives.
            max_matches: Maximum number of matches to return, or None for unlimited.

        Returns:
            List of matched cached values exceeding the threshold, ordered by score.
        """
        try:
            if not query_value or not cached_values:
                return []

            query_normalized = self._remove_accents(query_value.lower().strip())

            normalized_cache_map = {}
            for val in cached_values:
                norm_val = self._remove_accents(val.lower().strip())
                if norm_val not in normalized_cache_map:
                    normalized_cache_map[norm_val] = val

            normalized_cached_list = list(normalized_cache_map.keys())

            results = process.extract(
                query_normalized,
                normalized_cached_list,
                scorer=fuzz.WRatio,
                limit=max_matches,
                score_cutoff=threshold,
            )
            final_matches = []
            for match_str, _, _ in results:
                len_ratio = min(len(match_str), len(query_normalized)) / max(len(match_str), len(query_normalized), 1)
                if min_len_ratio is not None and len_ratio < min_len_ratio:
                    continue
                original_val = normalized_cache_map[match_str]
                final_matches.append(original_val)

            return final_matches
        except Exception:
            logger.exception(
                'Failed to perform fuzzy match.',
                extra={'query_value': query_value, 'cached_values': cached_values},
            )
            raise

    def _get_unique_cached_values(
        self, column: exp.Column, table_mapping: dict[str, str],
    ) -> list[str]:
        """Get deduplicated cached values for a column from Redis.

        Args:
            column: A sqlglot Column expression.
            table_mapping: Dict mapping alias/tables from ``_extract_table_mapping``.

        Returns:
            Deduplicated list of cached values, or empty list if none found.
        """
        column_str = self._get_column_name(column, table_mapping)
        cached_map = self._find_cached_values_for_column(column_str)

        if not cached_map:
            return []

        seen: set[str] = set()
        unique_cached: list[str] = []
        for v in (v for values in cached_map.values() for v in values):
            if v not in seen:
                seen.add(v)
                unique_cached.append(v)

        return unique_cached

    def _deduplicate_expressions(
        self, expressions: list[exp.Expression],
    ) -> list[exp.Expression]:
        """Deduplicate a list of sqlglot expressions, preserving order.

        String literals are deduplicated by value; non-string expressions are kept as-is.

        Args:
            expressions: List of sqlglot expressions to deduplicate.

        Returns:
            Deduplicated list of expressions.
        """
        seen: set[str] = set()
        result: list[exp.Expression] = []
        for expr in expressions:
            if isinstance(expr, exp.Literal) and expr.is_string:
                if expr.this not in seen:
                    seen.add(expr.this)
                    result.append(expr)
            else:
                result.append(expr)
        return result

    def _unwrap_operand(self, node: exp.Expression) -> exp.Column | None:
        """Unwrap a potentially function-wrapped column reference.

        Handles cases like LOWER(col), UPPER(col), TRIM(col) by extracting
        the inner Column node. Returns the Column if found, else None.

        Args:
            node: A sqlglot Expression to inspect.

        Returns:
            The inner ``exp.Column`` expression, or ``None`` if not found.
        """
        if isinstance(node, exp.Column):
            return node
        if isinstance(node, (exp.Lower, exp.Upper, exp.Trim)):
            inner = node.this
            if isinstance(inner, exp.Column):
                return inner
        return None

    def _unwrap_literal(self, node: exp.Expression) -> exp.Literal | None:
        """Unwrap a potentially function-wrapped string literal.

        Handles cases like LOWER('val'), UPPER('val'), TRIM('val') by extracting
        the inner Literal node. Returns the Literal if found, else None.

        Args:
            node: A sqlglot Expression to inspect.

        Returns:
            The inner ``exp.Literal`` expression, or ``None`` if not found.
        """
        if isinstance(node, exp.Literal) and node.is_string:
            return node
        if isinstance(node, (exp.Lower, exp.Upper, exp.Trim)):
            inner = node.this
            if isinstance(inner, exp.Literal) and inner.is_string:
                return inner
        return None

    def _extract_where_equality_conditions(
        self, expression: exp.Expression,
    ) -> list[dict]:
        """Extract WHERE column = 'string_literal' conditions from the SQL AST.

        Args:
            expression: A sqlglot Expression representing the parsed SQL query.

        Returns:
            List of dicts with keys ``column``, ``value``, and ``eq_node``.
        """
        try:
            conditions: list[dict] = []

            where = expression.find(exp.Where)
            if not where:
                return conditions

            for eq_node in where.find_all(exp.EQ):
                left = eq_node.left
                right = eq_node.right

                left_literal = self._unwrap_literal(left)
                if left_literal is not None and self._unwrap_operand(right) is not None:
                    left, right = right, left

                column = self._unwrap_operand(left)
                if column is None:
                    continue

                literal = self._unwrap_literal(right)
                if literal is None:
                    continue

                conditions.append({
                    'column': column,
                    'value': literal.this,
                    'eq_node': eq_node,
                })

            return conditions
        except Exception:
            logger.exception(
                'Failed to extract WHERE equality conditions from SQL expression.',
                extra={'expression': expression.sql() if expression else None},
            )
            raise

    def _extract_where_in_conditions(
        self, expression: exp.Expression,
    ) -> list[dict]:
        """Extract WHERE column IN ('val1', 'val2', ...) conditions from the SQL AST.

        Only extracts IN conditions where the column is a direct column reference
        and the IN list contains at least one string literal (not a subquery).

        Args:
            expression: A sqlglot Expression representing the parsed SQL query.

        Returns:
            List of dicts with keys ``column`` and ``in_node``.
        """
        try:
            conditions: list[dict] = []

            where = expression.find(exp.Where)
            if not where:
                return conditions

            for in_node in where.find_all(exp.In):
                # Unwrap function-wrapped columns (e.g. LOWER(col), UPPER(col), TRIM(col))
                column = self._unwrap_operand(in_node.this)
                if column is None:
                    continue

                in_expressions = in_node.expressions
                if not in_expressions:
                    continue

                has_string_literal = any(
                    isinstance(e, exp.Literal) and e.is_string
                    for e in in_expressions
                )
                if not has_string_literal:
                    continue

                conditions.append({
                    'column': column,
                    'in_node': in_node,
                })

            return conditions
        except Exception:
            logger.exception(
                'Failed to extract WHERE IN conditions from SQL expression.',
                extra={'expression': expression.sql() if expression else None},
            )
            raise

    def _process_eq_conditions(
        self,
        conditions: list[dict],
        table_mapping: dict[str, str],
        fuzzy_threshold: int,
        min_len_ratio: float | None,
        max_matches: int | None,
    ) -> None:
        """Apply fuzzy correction to WHERE column = 'value' conditions in-place.

        Args:
            conditions: Pre-extracted list of EQ conditions from
                ``_extract_where_equality_conditions``.
            table_mapping: Dict mapping alias/tables from ``_extract_table_mapping``.
            fuzzy_threshold: Minimum similarity score to accept a match.
            min_len_ratio: Minimum length ratio (0-1) for fuzzy match validity.
                Protects against substring false positives.
            max_matches: Maximum number of replacement values per condition.
        """
        try:
            for cond in conditions:
                column: exp.Column = cond['column']
                original_value: str = cond['value']
                eq_node: exp.EQ = cond['eq_node']

                unique_cached = self._get_unique_cached_values(column, table_mapping)
                if not unique_cached or original_value in unique_cached:
                    continue

                matches = self._fuzzy_match(original_value, unique_cached, fuzzy_threshold, min_len_ratio, max_matches)
                if not matches:
                    continue

                if len(matches) == 1:
                    new_node = exp.EQ(
                        this=column.copy(),
                        expression=exp.Literal.string(matches[0]),
                    )
                else:
                    new_node = exp.In(
                        this=column.copy(),
                        expressions=[exp.Literal.string(m) for m in matches],
                    )

                eq_node.replace(new_node)
        except Exception:
            logger.exception(
                'Failed to process EQ conditions for fuzzy correction.',
                extra={'conditions': conditions},
            )
            raise

    def _process_in_conditions(
        self,
        conditions: list[dict],
        table_mapping: dict[str, str],
        fuzzy_threshold: int,
        min_len_ratio: float | None,
        max_matches: int | None,
    ) -> None:
        """Apply fuzzy correction to WHERE column IN (...) conditions in-place.

        Args:
            conditions: Pre-extracted list of IN conditions from
                ``_extract_where_in_conditions``.
            table_mapping: Dict mapping alias/tables from ``_extract_table_mapping``.
            fuzzy_threshold: Minimum similarity score to accept a match.
            min_len_ratio: Minimum length ratio (0-1) for fuzzy match validity.
                Protects against substring false positives.
            max_matches: Maximum number of replacement values per original value.
        """
        try:
            for cond in conditions:
                column: exp.Column = cond['column']
                in_node: exp.In = cond['in_node']

                unique_cached = self._get_unique_cached_values(column, table_mapping)
                if not unique_cached:
                    continue

                new_expressions: list[exp.Expression] = []
                changed = False

                for item_expr in in_node.expressions:
                    if not isinstance(item_expr, exp.Literal) or not item_expr.is_string:
                        new_expressions.append(item_expr.copy())
                        continue

                    original_value = item_expr.this
                    if original_value in unique_cached:
                        new_expressions.append(item_expr.copy())
                        continue

                    matches = self._fuzzy_match(original_value, unique_cached, fuzzy_threshold, min_len_ratio, max_matches)
                    if matches:
                        new_expressions.extend(exp.Literal.string(m) for m in matches)
                        changed = True
                    else:
                        new_expressions.append(item_expr.copy())

                if not changed:
                    continue

                new_in_node = exp.In(
                    this=column.copy(),
                    expressions=self._deduplicate_expressions(new_expressions),
                )
                in_node.replace(new_in_node)
        except Exception:
            logger.exception(
                'Failed to process IN conditions for fuzzy correction.',
                extra={'conditions': conditions},
            )
            raise

    def process(self, input: AutocorrectorInput) -> AutocorrectorOutput:
        """Process the SQL query and apply fuzzy correction to WHERE clause values.

        Args:
            input: AutocorrectorInput containing the SQL query to correct.

        Returns:
            AutocorrectorOutput with the corrected SQL query.
        """
        sql_query = input.sql_query
        if not sql_query or not sql_query.strip():
            return AutocorrectorOutput(corrected_sql_query=sql_query)

        try:
            parsed_statements = sqlglot.parse(sql_query)
        except ParseError:
            return AutocorrectorOutput(corrected_sql_query=sql_query)

        if not parsed_statements:
            return AutocorrectorOutput(corrected_sql_query=sql_query)

        fuzzy_threshold = self.settings.fuzzy_threshold
        min_len_ratio = self.settings.min_len_ratio
        max_matches = self.settings.max_fuzzy_matches

        for expression in parsed_statements:
            if expression is None:
                continue
            table_mapping = self._extract_table_mapping(expression)
            eq_conditions = self._extract_where_equality_conditions(expression)
            in_conditions = self._extract_where_in_conditions(expression)
            self._process_eq_conditions(eq_conditions, table_mapping, fuzzy_threshold, min_len_ratio, max_matches)
            self._process_in_conditions(in_conditions, table_mapping, fuzzy_threshold, min_len_ratio, max_matches)

        corrected_sql = '; '.join(
            expr.sql() for expr in parsed_statements if expr is not None
        )
        return AutocorrectorOutput(corrected_sql_query=corrected_sql)
