"""Shared LLM factory with provider fallback.

Tries Groq first (fast, free daily quota). Falls back to OpenRouter on rate-limit,
auth, or connection errors. Both serve Llama 3.3 70B so output stays consistent.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import APIConnectionError as GroqAPIConnectionError
from groq import APIStatusError as GroqAPIStatusError
from groq import RateLimitError as GroqRateLimitError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()


# Exception types that should trigger fallback to OpenRouter.
_FALLBACK_EXCEPTIONS = (
    GroqRateLimitError,
    GroqAPIStatusError,
    GroqAPIConnectionError,
)


def make_llm(temperature: float = 0.1) -> BaseChatModel:
    """Return a chat model. Groq if available, OpenRouter as fallback."""
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if groq_key:
        primary = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=groq_key,
        )
        if openrouter_key:
            fallback = ChatOpenAI(
                model="meta-llama/llama-3.3-70b-instruct",
                temperature=temperature,
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            return primary.with_fallbacks(
                [fallback],
                exceptions_to_handle=_FALLBACK_EXCEPTIONS,
            )
        return primary

    if openrouter_key:
        return ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct",
            temperature=temperature,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )

    raise RuntimeError("No LLM key set. Add GROQ_API_KEY or OPENROUTER_API_KEY to .env.")
