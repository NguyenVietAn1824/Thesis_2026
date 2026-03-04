from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from functools import lru_cache

from aqi_agent.shared.models.memory import QAMemoryPair
from aqi_agent.shared.settings import Settings
from fastapi.requests import Request
from logger import get_logger

from .resources import Resources

logger = get_logger(__name__)


@lru_cache
def get_settings():
    return Settings()  # type: ignore


def get_resources(request: Request) -> Resources:
    return request.app.state.resources


def qa_message_to_string(messages: list[QAMemoryPair] | None):
    """
    Formats question and answer pairs to a string.

    Combines recent_messages with latest_message and converts QA pairs
    into a formatted string representation suitable for input to LLM models.

    Args:
        messages: List of question and answer pairs to format.

    Returns:
        str: Formatted string representation of messages.
    """
    if not messages:
        return ''

    messages_str = ''
    for message in messages:
        simple_message = message.simplize()
        if simple_message and len(simple_message) == 2:
            messages_str += f'User: {simple_message[0].get("content", "")}\nChatbot: {simple_message[1].get("content", "")}\n\n'

    return messages_str


async def semaphore_gather(
    *coroutines: Coroutine,
    max_coroutines: int,
):
    semaphore = asyncio.Semaphore(max_coroutines)

    async def _wrap_coroutine(coroutine):
        async with semaphore:
            return await coroutine

    return await asyncio.gather(*(_wrap_coroutine(coroutine) for coroutine in coroutines))
