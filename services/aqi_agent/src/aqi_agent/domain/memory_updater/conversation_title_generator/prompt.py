from __future__ import annotations

CONVERSATION_TITLE_GENERATOR_SYSTEM_PROMPT = """You generate a very short title for an air-quality assistant chat.

Use the same language as the user's messages (Vietnamese user → Vietnamese title).

**Vietnamese:** Keep địa danh exactly as in the conversation (*Giảng Võ*, *Cầu Giấy* — never romanized English forms). Title length about 5–12 words or a short Vietnamese phrase."""

CONVERSATION_TITLE_GENERATOR_USER_PROMPT = """Conversation messages:

{recent_messages}

Return one concise title in the user's language; preserve Vietnamese place names and diacritics."""
