# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lit-Agent** is a virtual librarian agent backed by a local ChromaDB vector store. It ingests `.txt` books from `library/`, embeds them, and exposes a LangChain agent with book management tools via a console UI.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the console UI (main entry point)
python main.py

# Re-sync vector DB manually
python rag/ingest.py

# Inspect ChromaDB contents
python rag/chroma_inspector.py
```

## Environment Setup

Copy `.env` and configure:

```env
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key
OPENAI_EMBED_MODEL=text-embedding-3-small

# Ollama (local)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

# Optional
AGENT_NAME=LitBot
PER_TOOL_THREAD_LIMIT=3   # max calls per tool per session thread
GLOBAL_TOOL_LIMIT=10      # max total tool calls per agent run
```

## Architecture

### Data Flow

```
library/*.txt  →  rag/ingest.py (TextLoader + RecursiveCharacterTextSplitter)
               →  rag/chroma_db/ (Chroma vector store, 500-char chunks, 100 overlap)
               →  agent/tools.py (retriever + LLM calls)
               →  agent/agent.py (LangChain agent + ToolCallLimitMiddleware)
               →  ui/console_ui.py (chat loop)
```

### Key Modules

- **`agent/llm_provider.py`** — Provider abstraction. `get_chat_llm()` and `get_embeddings()` return the correct LangChain objects based on `LLM_PROVIDER`. All other modules call through here.

- **`agent/agent.py`** — Creates the LangChain agent with `ToolCallLimitMiddleware` guards (prevents infinite tool cycles). Loads `domain_knowledge/*.md` files at import time into the system prompt — **restart required after editing domain knowledge**.

- **`agent/tools.py`** — Defines the 8 LangChain tools (`toolbox` list): `CreateBook`, `ReadBook`, `UpdateBookMetadata`, `RenameBook`, `ClassifyBook`, `GetContext`, `Summarize`, `MoralCreator`. All file operations are restricted to `library/` via path validation helpers. Metadata is stored as `.metadata.json` sidecars alongside each `.txt` book.

- **`rag/ingest.py`** — `ensure_books_ingested()` is called before every retrieval; it compares file mtimes/sizes against `rag/chroma_db/ingestion_state.json` and only re-ingests on changes. `ingest_books()` destroys and rebuilds the entire Chroma collection each run.

- **`rag/retriever.py`** — Canonical retriever module. `rag/retreiver.py` is a legacy misspelling kept as a re-export shim for backward compatibility — do not add new imports from the misspelled name.

- **`ui/console_ui.py`** — Session loop: streams agent output, auto-saves JSON session to `sessions/`, logs raw agent thinking to `sessions/*.log`. Has a guardrail that warns if a story-creation request doesn't produce a saved `.txt` path.

- **`scripts/extract_answer.py`** — Post-processes raw streamed agent output into a concise answer string. Called automatically after each turn and via `/extract`.

### Book Library Safety Rules

All tool-side file operations enforce:
1. Path must be a bare filename (no `/`, `\`, `..`, or absolute paths).
2. Resolved path must be inside `library/` (checked via `Path.relative_to()`).
3. Filenames are sanitized: only word chars, spaces, `.`, `-` kept; spaces → underscores.

### Auto-Ingestion

Before every vector search (`_get_vector_store()`), `ensure_books_ingested()` runs silently. Adding a `.txt` to `library/` takes effect on the next query without a manual restart. The state fingerprint lives at `rag/chroma_db/ingestion_state.json`.

### Domain Knowledge

`domain_knowledge/*.md` files are concatenated into the agent's system prompt at startup. Edit these to tune librarian classification behavior. Files are loaded in sorted filename order.
