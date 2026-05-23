# Lit-Agent

A virtual librarian agent backed by a local ChromaDB vector store. Lit-Agent can create original stories with an LLM pipeline, classify and analyse books, edit text with a full web editor, and answer questions grounded in your local `library/`.

The project ships two interfaces:

| Interface | Best for |
|---|---|
| **Web UI** (React + FastAPI) | Day-to-day use — chat, browse, read, and edit books side by side |
| **Console UI** | Scripting, quick CLI queries, session replay |

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 + | `python --version` |
| Node.js | 18 + | Only needed to build the frontend |
| npm | 9 + | Bundled with Node |
| An LLM | — | OpenAI API key **or** local [Ollama](https://ollama.com) |

---

## Quick start — Web UI

### 1. Clone and set up Python

```bash
git clone <repo-url>
cd Agents-research

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Minimum required fields — see [Configuration](#configuration) for all options.

### 3. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

The build output lands in `frontend/dist/`. FastAPI serves it automatically.

### 4. Start the server

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

> **Development mode** — run the Vite dev server alongside the API for hot-reload:
> ```bash
> # Terminal 1
> uvicorn api.main:app --port 8000 --reload
> # Terminal 2
> cd frontend && npm run dev   # proxies /api → port 8000
> ```
> Open **http://localhost:5173**

---

## Quick start — Console UI

```bash
python main.py
```

### Console commands

| Command | Description |
|---|---|
| `/help` | Show all available commands |
| `/exit` or `/quit` | End the session |
| `/history` | Print in-memory session history |
| `/save` | Save the session to `sessions/` |
| `/extract` | Run the answer extractor over raw session output |
| `/restore <id>` | Reload a previously saved session |
| `/reimport` | Re-ingest `library/` into ChromaDB |

---

## Configuration

All settings live in `.env`. Copy `.env.example` to get started.

### OpenAI

```env
AGENT_NAME=LitBot

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

OPENAI_API_KEY=sk-...
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### Ollama (local)

```env
AGENT_NAME=LitBot

LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Pull the required models before first run:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

### Optional tuning

```env
PER_TOOL_THREAD_LIMIT=3   # max calls to any single tool per agent run
GLOBAL_TOOL_LIMIT=20      # max total tool calls per agent run
```

---

## Web UI walkthrough

### Layout

The UI has three resizable panels — drag the dividers to resize:

```
┌──────────────┬─────────────────────┬──────────────────────┐
│   Sidebar    │    Book viewer      │      Chat            │
│              │                     │                      │
│  Library     │  Story text         │  Talk to LitBot      │
│  book list   │  ─────────────────  │                      │
│              │  Metadata / Analysis│                      │
│              │  Characters         │                      │
└──────────────┴─────────────────────┴──────────────────────┘
```

- **Sidebar** — lists all books in `library/`. Click a book to open it. Click again to close. The collapse button (‹) hides the sidebar to give more space.
- **Book viewer** — shows the story text. Collapsible metadata, analysis, and character panels on the right.
- **Chat** — send messages to LitBot. Responses stream token by token. The agent can create, edit, and analyse books on your behalf.

### Reading a book

Click any title in the sidebar. The centre panel opens with the full story text. Toggle **Hide info / Show info** to collapse the metadata panel.

### Editing a book by hand

Click the **✏️ pencil button** in the book header to enter edit mode. The story text becomes a textarea.

**Smart toolbar — Row 1:**

| Button | Effect |
|---|---|
| Fix spaces | Collapse double spaces, trim line ends, fold 3+ blank lines → 1 |
| Norm. breaks | CRLF → LF, normalise blank lines, trim document edges |
| Trim lines | Strip trailing whitespace from every line |
| " " Quotes | Straight quotes → typographic curly quotes |
| — Em dashes | `--` → `—` |
| … Ellipsis | `...` → `…` |
| Cap↑ Sentences | Capitalise first letter after `.` `!` `?` |
| ✦ Scene break | Insert `* * *` at the cursor position |
| ↩ Undo | Revert the last smart-tool transform (one level) |

Live word count, character count, and paragraph count are shown on the right of the toolbar.

**Smart toolbar — Row 2 (Find & Replace):**

Type in **Find** and **Replace with**, toggle **Aa** for case-sensitive matching, then click **Replace all** or press Enter. A green/red count appears inline.

When you are done, click **Save** to write the file to disk. **Cancel** discards all changes.

### Editing metadata

Click the **✏️** in the **Metadata** panel header. Six classification fields appear as text inputs: title, genre, theme, audience, reading level, moral. Click **✓** to save.

### Editing analysis

Click the **✏️** in the **Analysis** panel header. String fields (motivation, thesis, emotional arc, description) become resizable textareas. **Themes** is a free-form textarea — one theme per line. **Key moments** is a dynamic list: edit moment and explanation pairs, add rows with **+ Add moment**, delete with the trash icon. Click **✓** to save.

### Editing characters

Each character card has an **✏️** button that expands it into an inline form:

- **Name** — text input
- **Role** — dropdown: protagonist, antagonist, helper, rival, minor, other
- **Traits** — comma-separated text input
- **Arc** — resizable textarea
- **First appears** — text input

Click **Save** on a card to write it immediately. The world setting row (setting, time period, tone) is also click-to-edit. Use **+ Add character** to append a blank card, and **Delete** to remove one.

---

## Agent tools

LitBot has access to the following tools. You can trigger them by asking naturally — the agent chooses the right tool automatically.

### Story management

| Tool | What it does |
|---|---|
| `CreateBook` | Generate an original story with the LangGraph pipeline and save it to `library/` |
| `ReadBook` | Return the full text and metadata of a book |
| `EditBook` | Rewrite part or all of a story based on an instruction |
| `FindReplaceInBook` | Exact literal substitution across text and sidecars (rename a character, fix a typo) |
| `AppendToBook` | Generate and append a new section or chapter |
| `ChangeWritingStyle` | Rewrite the whole story in a different tone (e.g. "whimsical fairy tale", "noir") |
| `DeleteBook` | Permanently remove a book and all its sidecars — only on explicit user request |
| `RenameBook` | Rename the `.txt` file and update sidecar references |

### Library & discovery

| Tool | What it does |
|---|---|
| `ListBooks` | Catalogue all books with title, genre, word count — no vector search |
| `SearchLibrary` | Filter by genre, theme, audience, or keyword |
| `GetBookStats` | Word count, character count, sentence count, reading time |
| `GetContext` | Retrieve grounded passages via vector similarity |

### Classification & analysis

| Tool | What it does |
|---|---|
| `ClassifyBook` | Genre, theme, audience, reading level, rationale |
| `AnalyzeStory` | Motivation, thesis, themes, key moments, emotional arc |
| `Summarize` | Concise librarian-style summary |
| `MoralCreator` | Extract or infer the moral / lesson |
| `ExtractQuotes` | Pull the most memorable quotes with significance notes |
| `GenerateQuiz` | Reading comprehension questions at mixed difficulty levels |

### Metadata & characters

| Tool | What it does |
|---|---|
| `UpdateBookMetadata` | Update classification fields in the metadata sidecar |
| `GetCharacterList` | List name, role, traits, arc from `.characters.json` |
| `UpdateCharacter` | Update a single character's name, role, traits, or arc |

---

## Project structure

```
Agents-research/
├── agent/
│   ├── agent.py          # LangGraph agent, system prompt, tool-call middleware
│   ├── tools.py          # All 21 LangChain tools + file safety helpers
│   └── llm_provider.py   # OpenAI / Ollama abstraction
│
├── api/
│   ├── main.py           # FastAPI app, lifespan (agent warmup), static serving
│   └── routes/
│       ├── library.py    # CRUD endpoints for books, metadata, analysis, characters
│       ├── chat.py       # POST /chat  +  GET /stream/{run_id}  (SSE)
│       └── system.py     # GET /health, POST /reimport, GET /session/{id}
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts            # Typed API client
│   │   ├── components/
│   │   │   ├── Layout.tsx        # Three-panel resizable layout
│   │   │   ├── Sidebar.tsx       # Book list
│   │   │   ├── StoryView.tsx     # Book viewer + edit mode
│   │   │   ├── StoryText.tsx     # Read / textarea edit
│   │   │   ├── EditToolbar.tsx   # Smart editing toolbar
│   │   │   ├── MetadataPanel.tsx # Classification view + edit
│   │   │   ├── AnalysisPanel.tsx # Literary analysis view + edit
│   │   │   ├── CharacterPanel.tsx# Characters view + edit
│   │   │   ├── ChatView.tsx      # Chat interface
│   │   │   └── Message.tsx       # Single chat bubble
│   │   └── hooks/
│   │       ├── useLibrary.ts     # React Query hooks for all library endpoints
│   │       ├── useChat.ts        # Chat + SSE stream state
│   │       └── useLocalState.ts  # localStorage-backed state
│   └── package.json
│
├── pipeline/
│   ├── graph.py          # LangGraph story-generation pipeline
│   ├── nodes.py          # Planner, writer, critic, editor nodes
│   ├── rubric.py         # Critic scoring rubric
│   └── state.py          # Pipeline state schema
│
├── rag/
│   ├── constants.py      # LIBRARY_DIR, DB_PATH, COLLECTION_NAME
│   ├── ingest.py         # TextLoader + splitter, mtime-based change detection
│   ├── retriever.py      # Per-book and global retriever factory
│   └── chroma_db/        # Vector store (git-ignored, auto-rebuilt)
│
├── domain_knowledge/     # Markdown files loaded into the agent system prompt
├── library/              # Plain-text books (.txt) + sidecars (.metadata.json, .characters.json)
├── sessions/             # Saved console sessions (git-ignored)
├── ui/
│   └── console_ui.py     # Interactive console loop
└── main.py               # Entry point for console UI
```

---

## Library file format

Each book in `library/` is a plain `.txt` file. Two JSON sidecars live next to it:

```
library/
  my_story.txt                  ← narrative text
  my_story.metadata.json        ← classification, analysis, pipeline metrics, edit history
  my_story.characters.json      ← character roster and world data
```

**`*.metadata.json` shape:**
```json
{
  "book_name": "my_story",
  "source_path": "library/my_story.txt",
  "classification": {
    "title": "My Story",
    "genre": "fable",
    "theme": "courage",
    "audience": "children",
    "reading_level": "easy",
    "moral": "Small acts of bravery matter."
  },
  "analysis": {
    "motivation": "...",
    "thesis": "...",
    "thoughts": ["theme 1", "theme 2"],
    "key_moments": [{ "moment": "...", "explanation": "..." }],
    "brief_description": "...",
    "emotional_arc": "..."
  },
  "pipeline": {
    "critic_score": 0.87,
    "critic_passes": 2,
    "stages_completed": ["plan", "write", "critique", "edit"]
  },
  "edit_history": [
    { "timestamp": "2026-05-23T12:00:00Z", "instruction": "Make the ending happier", "section_hint": null }
  ]
}
```

---

## API reference

All endpoints are prefixed with `/api`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | LLM provider info and status |
| `POST` | `/chat` | Start a chat run; returns `{ run_id }` |
| `GET` | `/stream/{run_id}` | SSE stream of `token`, `tool_call`, `done` events |
| `GET` | `/library` | List all books (name, classification, version) |
| `GET` | `/library/{name}` | Full book detail (text + all metadata) |
| `PUT` | `/library/{name}` | Save new text content |
| `PUT` | `/library/{name}/metadata` | Update classification fields |
| `PUT` | `/library/{name}/analysis` | Update analysis fields |
| `GET` | `/library/{name}/analysis` | Get analysis block |
| `PUT` | `/library/{name}/characters` | Save full character roster |
| `GET` | `/library/{name}/characters` | Get character roster |
| `POST` | `/reimport` | Rebuild the ChromaDB vector index from `library/` |
| `GET` | `/session/{id}` | Retrieve a saved console session |

---

## Domain knowledge

Files in `domain_knowledge/*.md` are concatenated into the agent system prompt at startup in alphabetical order. Edit them to tune how LitBot classifies, analyses, or writes stories. **Restart the server after any change** — the content is loaded once at import time.

---

## Automatic ingestion

Before every vector search the ingestor compares file modification times against `rag/chroma_db/ingestion_state.json`. A changed or new `.txt` file triggers a full index rebuild transparently. To force a rebuild manually:

```bash
python rag/ingest.py
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `OPENAI_API_KEY` error | Add the key to `.env` |
| Ollama connection refused | Run `ollama serve` and confirm the model is pulled |
| First `/chat` is slow | Normal on first run — the agent initialises lazily. Subsequent calls are fast. |
| Stories look generic | Increase `GLOBAL_TOOL_LIMIT` or `recursion_limit` in `api/routes/chat.py` |
| Vector search returns nothing | Run `python rag/ingest.py` to rebuild the index |
| `domain_knowledge` changes ignored | Restart the server — content loads at startup only |
| Frontend 404 after `npm run build` | Confirm `frontend/dist/` exists; rebuild with `npm run build` |
| TypeScript errors in frontend | Run `cd frontend && npx tsc --noEmit` to see full output |

---

## License

See `LICENSE.md`.
