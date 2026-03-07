from __future__ import annotations

from base import BaseModel


class Correction(BaseModel):
    original_value: str
    corrected_values: list[str]
