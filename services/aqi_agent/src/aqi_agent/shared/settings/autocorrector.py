from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AutocorrectorSettings(BaseModel):
  """Configuration settings for SQL fuzzy correction service.

  Attributes:
      redis_key_prefix: Prefix used to store frequent column values in Redis.
          Format: ``<prefix>:<table_name>.<column_name>``.
      fuzzy_threshold: Minimum similarity score (0-100) for fuzzy matching.
          A match is accepted if its score meets or exceeds this threshold.
      min_len_ratio: Minimum length ratio (0-1) for fuzzy match validity.
          Protects against substring false positives: e.g. "ge" matching "woodenbridge"
          due to partial_ratio. The shorter string must be at least this fraction
          of the longer string's length. Default 0.4 means 40% length ratio minimum.
          This allows short district names (e.g. "ba đinh") to match prefixed
          cached values (e.g. "Phường Ba Đình").
      max_fuzzy_matches: Maximum number of fuzzy matches to return per condition.
          If None, returns all matches above threshold. If set (e.g. 5),
          limits results to top 5 best matches.
  """
  redis_key_prefix: str = 'frequent_values:'
  fuzzy_threshold: int = 70
  min_len_ratio: float = 0.4
  max_fuzzy_matches: Optional[int] = 5
