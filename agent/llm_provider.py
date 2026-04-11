import os
import importlib

from dotenv import load_dotenv

load_dotenv()


def get_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "ollama"}:
        raise ValueError(
            "Invalid LLM_PROVIDER. Expected 'openai' or 'ollama'. "
            f"Got: {provider!r}"
        )
    return provider


def get_chat_model_name() -> str:
    provider = get_llm_provider()
    if provider == "openai":
        return os.getenv("LLM_MODEL", "gpt-4o-mini")
    return os.getenv("LLM_MODEL", "llama3.1")


def get_chat_llm(temperature: float = 0.0):
    provider = get_llm_provider()
    model_name = get_chat_model_name()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    try:
        ollama_module = importlib.import_module("langchain_ollama")
        ChatOllama = getattr(ollama_module, "ChatOllama")
    except Exception as exc:
        raise ImportError(
            "Ollama support requires langchain-ollama. Install it with: pip install langchain-ollama"
        ) from exc

    return ChatOllama(model=model_name, temperature=temperature, base_url=base_url)


_embeddings_cache: dict = {}


def get_embeddings():
    provider = get_llm_provider()
    if provider in _embeddings_cache:
        return _embeddings_cache[provider]

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )
        from langchain_openai import OpenAIEmbeddings

        model_name = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        instance = OpenAIEmbeddings(model=model_name, api_key=api_key)
    else:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        try:
            ollama_module = importlib.import_module("langchain_ollama")
            OllamaEmbeddings = getattr(ollama_module, "OllamaEmbeddings")
        except Exception as exc:
            raise ImportError(
                "Ollama embeddings require langchain-ollama. Install it with: pip install langchain-ollama"
            ) from exc
        instance = OllamaEmbeddings(model=embed_model, base_url=base_url)

    _embeddings_cache[provider] = instance
    return instance
