# Lit-Agent

Lit-Agent is a small toolkit and example agent for working with a local book library. It now behaves more like a virtual librarian: it can classify books, summarize them, extract morals, create new stories, and manage files in `library/` safely.

## Key features
- Book ingestion: split and preprocess plain-text books into chunks for embedding.
- Vector store: local Chroma/SQLite-backed embedding database for similarity search.
- Automatic ingestion sync: retrieval checks whether `library/` or `books/` changed and re-ingests when needed.
- Librarian tools: classify books, read books, create books, update metadata, and rename books inside `library/`.
- Domain knowledge: compact librarian reference notes are loaded from `domain_knowledge/` at startup.
- RAG workflows: combine retrieved passages with LLM prompts to produce grounded answers, summaries, and morals.

## Repository layout
- `agent/` - agent logic and helper tools
- `rag/` - ingestion, retriever, and Chroma DB utilities
- `library/` - active plain-text books source directory
- `books/` - optional legacy/fallback books directory
- `domain_knowledge/` - librarian rules, taxonomy, examples, and metadata guidance
- `rag/chroma_db/` - local Chroma/SQLite database files
- `sessions/` - saved chat sessions and logs
- `main.py` - example runner

## Quick start

1. Create a virtual environment and activate it:
```powershell
python -m venv .venv
.venv\Scripts\activate
```
2. Install dependencies:
```powershell
pip install -r requirements.txt
```
3. Run the app:
```powershell
python main.py
```

## Console UI

The app provides a session-style console UI launched by `python main.py`.

Available commands inside the UI:
- `/help` - show help and command descriptions
- `/exit` or `/quit` - exit the session
- `/history` - show in-memory session history
- `/save` - save the current session to `sessions/`
- `/extract` - run the concise-answer extractor over raw session output
- `/restore <session-id-or-name>` - restore a previously saved session
- `/reimport` - re-ingest books from `library/` (fallback: `books/`) into ChromaDB

## Library management tools

The agent now exposes explicit book-management tools through its prompt layer:
- `ClassifyBook` - classify a book with genre, theme, audience, reading level, and rationale
- `CreateBook` - create an original book and save it in `library/`
- `ReadBook` - read a book from `library/` safely
- `UpdateBookMetadata` - update a book's metadata sidecar in `library/`
- `RenameBook` - rename a book safely inside `library/`
- `GetContext` - retrieve grounded passages for classification or analysis
- `Summarize` - summarize book passages in librarian style
- `MoralCreator` - extract or infer the moral or lesson

### Safety rules
- File operations are restricted to `library/`.
- Path traversal and absolute path escapes are rejected.
- Metadata is stored next to each book as a `.metadata.json` sidecar.

## Domain knowledge

The agent loads compact librarian reference notes from `domain_knowledge/` at startup. These notes provide stable guidance for:
- classification,
- library organization,
- narrative pattern recognition,
- metadata structure,
- and moral/lesson extraction.

If you update files in `domain_knowledge/`, restart the agent so the revised knowledge is included in the system prompt.

## Automatic ingestion behavior

- Source directory priority:
  1. `library/` if present
  2. `books/`
- Before retrieval, the app compares the current `.txt` files against `rag/chroma_db/ingestion_state.json`.
- If files were added, updated, or removed, the vector DB is rebuilt automatically.

### Verify auto ingestion
1. Add a new `.txt` file to `library/`.
2. Start the app with `python main.py`.
3. Ask a question that should match the new file.
4. Confirm the answer includes retrieved context from that file.

You can also run:
```powershell
python rag/ingest.py
```
to re-sync the index manually.

## Examples

### Ask for a summary
```text
You: Summarize the moral of The Proud Rose
```

### Create a new book
Ask the agent to create a story and save it in the library:
```text
Create a short fable about patience and save it in library/
```

### Classify a book
```text
Classify The Ant and the Grasshopper
```

## Configuration
- Set provider configuration in `.env`.
- `LLM_PROVIDER` supports `openai` or `ollama`.
- `LLM_MODEL` is shared and should match the selected provider.
- `AGENT_NAME` changes the displayed agent name.

### OpenAI example
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### Ollama example
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
```

### Ollama local setup
```powershell
# Option A: start the local Ollama runtime explicitly
ollama serve

# Option B: launch runtime via Ollama launch workflow
ollama launch

# Pull models used by this project
ollama pull llama3.1
ollama pull nomic-embed-text
```

- The local Chroma DB path defaults to `rag/chroma_db/`.

## Troubleshooting
- Ensure book files are UTF-8 encoded if ingestion fails.
- Improve retrieval quality by adjusting chunk size or the embedding model.
- Restart the app after editing files in `domain_knowledge/`.
- If `LLM_PROVIDER=ollama`, ensure Ollama is running and the configured models are pulled.
- If `LLM_PROVIDER=openai`, ensure `OPENAI_API_KEY` is present.

## License
- See `LICENSE.md` for license details.
