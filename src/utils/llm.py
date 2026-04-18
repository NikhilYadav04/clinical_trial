"""
Shared LLM factory.

Supports two providers — set LLM_PROVIDER in .env:
  LLM_PROVIDER=ollama   → local Ollama (no rate limits, free)
  LLM_PROVIDER=gemini   → Google Gemini API (default)

Ollama setup:
  1. Install: https://ollama.com
  2. Pull a model: ollama pull llama3.2
  3. Set in .env: LLM_PROVIDER=ollama
                  OLLAMA_MODEL=llama3.2
"""

import os
from langchain_core.language_models.chat_models import BaseChatModel


def get_llm(temperature: float = 0, model: str = None) -> BaseChatModel:
    """
    Return a configured LLM instance based on LLM_PROVIDER env variable.

    Args:
        temperature: 0 for structured extraction, 0.3 for report writing
        model:       Override model name (uses env default if not set)
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "ollama":
        return _get_ollama(temperature, model)
    else:
        return _get_gemini(temperature, model)


def _get_gemini(temperature: float, model: str = None) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "Gemini API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env"
        )

    return ChatGoogleGenerativeAI(
        model=model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview"),
        temperature=temperature,
        google_api_key=key,
    )


def _get_ollama(temperature: float, model: str = None) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    ollama_model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    base_url     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return ChatOllama(
        model=ollama_model,
        temperature=temperature,
        base_url=base_url,
        timeout=120,          # 2 min max per call — prevents silent hangs
        num_predict=1024,     # cap output tokens so it doesn't ramble
    )
