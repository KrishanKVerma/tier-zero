"""Shared LLM factory with provider fallback.

Determinism policy (Day 20):
- temperature defaults to 0.0 for reproducible scoring.
- Groq's llama-3.3-70b-versatile is the canonical model.
- OpenRouter fallback also uses llama-3.3-70b-instruct (closest match to canonical)
  so a fallback doesn't swing the verdict to a different model family.
- Fallback only triggers on rate-limit / connection / status errors, and logs loudly.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from groq import APIConnectionError as GroqAPIConnectionError
from groq import APIStatusError as GroqAPIStatusError
from groq import RateLimitError as GroqRateLimitError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger("tier_zero.llm")

# Canonical model. Both providers serve the same Llama 3.3 70B family
# so a fallback stays as close as possible to the primary's judgment.
_GROQ_MODEL = "llama-3.3-70b-versatile"
_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"

_FALLBACK_EXCEPTIONS = (
    GroqRateLimitError,
    GroqAPIStatusError,
    GroqAPIConnectionError,
)


def make_llm(temperature: float = 0.0) -> BaseChatModel:
    """Return a chat model. Groq canonical, OpenRouter fallback (same model family).

    temperature defaults to 0.0 for deterministic, reproducible output.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if groq_key:
        primary = ChatGroq(
            model=_GROQ_MODEL,
            temperature=temperature,
            api_key=groq_key,
        )
        if openrouter_key:
            fallback = ChatOpenAI(
                model=_OPENROUTER_MODEL,
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
        logger.warning("No GROQ_API_KEY set; using OpenRouter as primary.")
        return ChatOpenAI(
            model=_OPENROUTER_MODEL,
            temperature=temperature,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )

    raise RuntimeError("No LLM key set. Add GROQ_API_KEY or OPENROUTER_API_KEY to .env.")