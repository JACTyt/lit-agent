# Lit-Agent

Lit-Agent is a small toolkit and example agent for building retrieval-augmented workflows over plain-text books. The project provides utilities to ingest books, create a local vector store, and run an agent that uses retrieval + LLM prompts to answer questions, summarize, and extract facts grounded in the source text.

Key features
- Book ingestion: split and preprocess plain-text books into chunks for embedding.
- Vector store: local Chroma/SQLite-backed embedding database for fast similarity search.
- Agent tools: scripts and helper functions to query, summarize, and extract structured data.
- RAG workflows: combine retrieved passages with LLM prompts to produce grounded answers.
- Automatic ingestion sync: retrieval checks whether `library/` or `books/` changed and re-ingests when needed.

Quick start

1. Create a virtual environment and activate it:
```powershell
python -m venv .venv
.venv\Scripts\activate
```
2. Install dependencies (if `requirements.txt` exists):
```powershell
pip install -r requirements.txt
```
3. Run the example entrypoint:
```powershell
python main.py
```

Interactive Console UI
----------------------

The project now provides a simple session-style console UI (launched by `python main.py`). The UI supports multi-turn chats, automatic session autosave, per-session log files, and a few convenience commands.

- Start the UI:

```powershell
python main.py
```

- When a session starts you will see a session id printed (for example `20260308T113317-16957d`). The session autosaves to `sessions/session_<id>.json` and a live log is written to `sessions/session_<id>.log`.
- Commands (type them at the prompt):
	- `/help` : show help and command descriptions
	- `/exit` or `/quit` : exit the session
	- `/history` : display the in-memory session history (user inputs + concise AI replies)
	- `/save` : save the current session to `sessions/<safe_name>.json` and copy the live log to `sessions/<safe_name>.log`
	- `/extract` : run the concise-answer extractor over the session raw outputs and show the extracted summary
	- `/restore <session-id-or-name>` : restore a previously saved session by id or filename fragment (loads its history into the current session)

Autosave and Logs
-----------------

- An autosave JSON is created at session start and updated after every user action: `sessions/session_<id>.json`.
- A live per-session log file is created at session start: `sessions/session_<id>.log`.
- When you use `/save` and provide a name, the autosave JSON and the live log are copied to `sessions/<safe_name>.json` and `sessions/<safe_name>.log`.

Agent configuration
-------------------

- Set provider/keys as environment variables (for example `OPENAI_API_KEY`).
- Optional environment overrides:
	- `AGENT_NAME` to change the displayed agent name (default `LitBot`).
	- `LLM_MODEL` to choose a different model string used by the agent (default `gpt-4o-mini`).

Examples
--------

- Start and ask a question:

```powershell
python main.py
You: Summarize the moral of The Proud Rose
```

- Save the session after a few turns:

```text
/save
Session name (optional): proud_rose_notes
```

The session JSON and named log will be available in the `sessions/` folder.

Typical workflow
- Ingest/sync books: `python rag/ingest.py`
- Inspect DB: `python rag/chroma_inspector.py`
- Query agent: `python main.py --query "Summarize the moral of The Ant and the Grasshopper"`

Automatic ingestion behavior
---------------------------

- Source directory priority:
	1. `library/` (if present)
	2. `books/`
- Before retrieval, the app compares current `.txt` files (name, size, mtime) against `rag/chroma_db/ingestion_state.json`.
- If files were added/updated/removed, the vector DB is rebuilt automatically.

How to verify auto ingestion
----------------------------

1. Add a new `.txt` file into `library/` (or `books/` if `library/` does not exist).
2. Start the app with `python main.py`.
3. Ask a question that should match content from the new file.
4. Confirm the answer includes retrieved context from that file.

You can also run `python rag/ingest.py` directly to see whether ingestion runs or reports that the index is already up to date.

Repository layout
- `agent/` — agent logic and helper tools
- `rag/` — ingestion, retriever, and Chroma DB utilities
- `library/` — active plain-text books source directory
- `books/` — optional legacy/fallback books directory
- `domain_knowledge/` — librarian rules, taxonomy, and examples loaded into the agent prompt
- `rag/chroma_db/` — local Chroma/SQLite database files
- `main.py` — example runner

Domain knowledge
-----------------

The agent now loads compact librarian reference notes from `domain_knowledge/` at startup. These notes provide stable guidance for:
- classification,
- library organization,
- and moral/lesson extraction.

If you update the files in `domain_knowledge/`, restart the agent so the revised knowledge is included in the system prompt.

Configuration
- Set any required LLM provider API keys as environment variables (for example `OPENAI_API_KEY`).
- The local Chroma DB path defaults to `rag/chroma_db/`; change paths in the configuration or scripts if needed.

Contributing
- Fork the repo, create a branch, add focused changes and tests, then open a pull request.

Troubleshooting
- Ensure book files are UTF-8 encoded if ingestion fails.
- Improve retrieval quality by adjusting chunk size or the embedding model.

License
- See `LICENSE.md` for license details.