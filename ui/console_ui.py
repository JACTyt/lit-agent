"""Simple console chat UI for the Lit-Agent (session-style).

Provides a friendly chat loop, session history, and saves sessions to disk.
"""
from agent.agent import init_agent, AGENT_NAME
from scripts.extract_answer import extract_answer
from rag.ingest import ingest_books
import datetime
import os
import json
import logging
import re
import shutil
import uuid
from pathlib import Path


def _safe_filename(name: str) -> str:
    return "session_" + "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')


def _looks_like_story_create_request(text: str) -> bool:
    lowered = (text or "").lower()
    asks_create = any(word in lowered for word in ("create", "generate", "write", "save"))
    asks_story = any(word in lowered for word in ("story", "book", "fable", "tale"))
    return asks_create and asks_story


def _has_saved_path_signal(text: str) -> bool:
    content = text or ""
    if "status\": \"created\"" in content.lower():
        return True
    # Detect either JSON-like path keys or plain absolute/relative txt paths.
    if re.search(r'"path"\s*:\s*"[^"]+\.txt"', content, flags=re.IGNORECASE):
        return True
    if re.search(r'\b[a-zA-Z]:\\[^\n\r]*\.txt\b', content):
        return True
    if re.search(r'\blibrary[\\/][^\n\r]*\.txt\b', content, flags=re.IGNORECASE):
        return True
    return False


def _normalize_label(value: str) -> str:
    return re.sub(r"[\W_]+", "", (value or "").lower())


def _extract_created_title(text: str) -> str | None:
    content = text or ""
    # Common response forms: The book "Title" has been created ...
    m = re.search(r'the\s+book\s+"([^"]+)"\s+has\s+been\s+created', content, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Also allow Title: ... style
    m = re.search(r'\btitle\s*:\s*([^\n\r]+)', content, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"')
    return None


def _resolve_story_path_from_title(text: str, library_dir: str = "library") -> str | None:
    title = _extract_created_title(text)
    if not title:
        return None

    lib = Path(library_dir)
    if not lib.exists():
        return None

    normalized_title = _normalize_label(title)
    matches = [p for p in lib.glob("*.txt") if _normalize_label(p.stem) == normalized_title]
    if len(matches) == 1:
        return str(matches[0].resolve())
    if len(matches) > 1:
        newest = max(matches, key=lambda p: p.stat().st_mtime)
        return str(newest.resolve())

    return None


def _extract_saved_txt_path(text: str) -> str | None:
    content = text or ""

    # Prefer explicit JSON "path" values from tool output.
    m = re.search(r'"path"\s*:\s*"([^"]+\.txt)"', content, flags=re.IGNORECASE)
    if m:
        candidate = m.group(1).replace('\\\\', '\\').strip()
        return candidate

    # Fall back to absolute Windows paths.
    m = re.search(r'\b([a-zA-Z]:\\[^\n\r]*?\.txt)\b', content)
    if m:
        return m.group(1).strip()

    # Fall back to library-relative paths.
    m = re.search(r'\b(library[\\/][^\n\r]*?\.txt)\b', content, flags=re.IGNORECASE)
    if m:
        return os.path.abspath(m.group(1).replace('/', os.sep).replace('\\', os.sep).strip())

    return None


def _read_saved_story_from_output(raw_output: str) -> tuple[str, str] | tuple[None, None]:
    path = _extract_saved_txt_path(raw_output)
    if not path:
        path = _resolve_story_path_from_title(raw_output)
    if not path:
        return None, None
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if not os.path.exists(path):
        return path, None

    try:
        return path, Path(path).read_text(encoding="utf-8")
    except Exception:
        return path, None


def run(session_dir: str = "sessions"):
    os.makedirs(session_dir, exist_ok=True)
    session_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    log_path = os.path.join(session_dir, f"session_{session_id}.log")
    logger = _setup_logger(log_path)
    agent = init_agent()
    history = []
    autosave_path = os.path.join(session_dir, f"session_{session_id}.json")
    # show session id and instructions
    print(f"Starting chat with {AGENT_NAME}. Session id: {session_id}")
    print("Type /help for commands.")
    # initial autosave (empty history)
    try:
        with open(autosave_path, "w", encoding="utf-8") as fh:
            json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass

    while True:
        user_input = input("You: ")
        if not user_input:
            continue
        if user_input.startswith("/"):
            cmd = user_input.strip().lower()
            if cmd in ("/exit", "/quit"):
                print("Exiting session.")
                break
            if cmd == "/help":
                help_lines = [
                    "Available commands:",
                    "  /help     : Show this help message",
                    "  /exit     : Exit the chat session",
                    "  /history  : Show in-memory session history (user + concise AI replies)",
                    "  /save     : Save the current session to a JSON file in the sessions/ folder",
                    "  /extract  : Run the concise-answer extractor over the session raw outputs",
                    "  /restore <id> : Restore a previously saved session by id or name",
                    "  /reimport : Re-ingest books from library/ (fallback: books/) into ChromaDB",
                ]
                help_text = "\n".join(help_lines)
                print(help_text)
                # record command and its printed output
                history.append({"user": user_input, "ai": help_text, "raw": ""})
                try:
                    with open(autosave_path, "w", encoding="utf-8") as fh:
                        json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                continue
            if cmd == "/history":
                for i, turn in enumerate(history, 1):
                    print(f"{i}. You: {turn['user']}")
                    print(f"   {AGENT_NAME}: {turn['ai']}")
                # record the command invocation
                history.append({"user": user_input, "ai": "Displayed history", "raw": ""})
                try:
                    with open(autosave_path, "w", encoding="utf-8") as fh:
                        json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                continue
            if cmd.startswith("/restore"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Usage: /restore <session-id-or-name>")
                    continue
                target = parts[1].strip()
                # find json files that contain the target string
                candidates = [f for f in os.listdir(session_dir) if f.endswith('.json') and target in f]
                if not candidates:
                    # try exact matches
                    if os.path.exists(os.path.join(session_dir, target)):
                        candidate = target
                    elif os.path.exists(os.path.join(session_dir, target + '.json')):
                        candidate = target + '.json'
                    else:
                        print(f"No session found matching '{target}' in {session_dir}")
                        continue
                else:
                    candidate = candidates[0]
                path = os.path.join(session_dir, candidate)
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    history = data.get('history', [])
                    # update autosave and session_id if present
                    session_id = data.get('session_id', session_id)
                    autosave_path = os.path.join(session_dir, f"session_{session_id}.json")
                    with open(autosave_path, 'w', encoding='utf-8') as fh:
                        json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                    print(f"Restored {len(history)} turns from {candidate}")
                except Exception as e:
                    print("Failed to restore session:", e)
                continue
            if cmd == "/save":
                name = input("Session name (optional): ").strip() or datetime.datetime.now().isoformat()
                safe = _safe_filename(name)
                fname = safe + ".json"
                path = os.path.join(session_dir, fname)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump({"history": history, "agent": AGENT_NAME, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                # also copy the session log to a named file matching the session
                try:
                    new_log = os.path.join(session_dir, safe + ".log")
                    shutil.copy(log_path, new_log)
                    print(f"Saved session to {path} and log to {new_log}")
                except Exception:
                    print(f"Saved session to {path} (log copy failed)")
                # also copy autosave JSON to named file
                try:
                    named_json = os.path.join(session_dir, safe + ".json")
                    shutil.copy(autosave_path, named_json)
                except Exception:
                    pass
                continue
            if cmd == "/extract":
                if not history:
                    print("No messages yet to extract from.")
                    continue
                raw = "\n\n".join(turn.get("raw", "") for turn in history)
                extracted = extract_answer(raw)
                print("Extracted:")
                print(extracted)
                history.append({"user": user_input, "ai": extracted, "raw": ""})
                try:
                    with open(autosave_path, "w", encoding="utf-8") as fh:
                        json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                continue
            if cmd == "/reimport":
                print("Re-importing books from library/ (fallback: books/) ...")
                try:
                    vectorstore, vector_count = ingest_books()
                    result_msg = f"Successfully re-imported ChromaDB with {vector_count} vectors!"
                    print(result_msg)
                    history.append({"user": user_input, "ai": result_msg, "raw": ""})
                    try:
                        with open(autosave_path, "w", encoding="utf-8") as fh:
                            json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                except Exception as e:
                    error_msg = f"Failed to re-import books: {e}"
                    print(error_msg)
                    history.append({"user": user_input, "ai": error_msg, "raw": ""})
                    try:
                        with open(autosave_path, "w", encoding="utf-8") as fh:
                            json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                continue
            print("Unknown command. Type /help for commands.")
            continue

        # Send user input to agent and stream reply
        collected = ""
        try:
            for step in agent.stream({"messages": [{"role": "user", "content": user_input}]}):
                raw = str(step)
                collected += raw
                try:
                    logger.info(raw)
                except Exception:
                    pass
        except Exception as e:
            logger.exception("Agent stream error: %s", e)
            print("Agent stream error:", e)
            continue

        # Use full output for story-creation prompts and concise output otherwise.
        wants_story_output = _looks_like_story_create_request(user_input)
        if wants_story_output:
            saved_path, saved_story = _read_saved_story_from_output(collected)
            if saved_path and saved_story:
                shown = f"Saved to: {saved_path}\n\n{saved_story}"
            else:
                shown = extract_answer(collected, concise=False, max_chars=None)
        else:
            shown = extract_answer(collected)
        print(f"{AGENT_NAME}: {shown}")

        # Guardrail: detect create/save story requests that did not persist a file.
        if wants_story_output:
            combined_output = f"{collected}\n{shown}"
            if not _has_saved_path_signal(combined_output):
                warning = (
                    "Warning: your request looked like story creation, but no saved .txt path was detected. "
                    "Ask again with: 'Create and save the story into library/'."
                )
                print(f"{AGENT_NAME}: {warning}")

        history.append({"user": user_input, "ai": shown, "raw": collected})
        # Log concise answer
        try:
            logger.info("User: %s", user_input)
            logger.info("Shown: %s", shown)
        except Exception:
            pass
        # autosave session after each interaction
        try:
            with open(autosave_path, "w", encoding="utf-8") as fh:
                json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _setup_logger(log_path: str):
    logger = logging.getLogger("agent_thinking")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

