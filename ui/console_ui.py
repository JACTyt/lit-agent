"""Simple console chat UI for the Lit-Agent (session-style).

Provides a friendly chat loop, session history, and saves sessions to disk.
"""
from agent.agent import init_agent, AGENT_NAME
from scripts.extract_answer import extract_answer
import datetime
import os
import json
import logging
import sys


def _safe_filename(name: str) -> str:
    return "session_" + "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')


def run(session_dir: str = "sessions"):
    os.makedirs(session_dir, exist_ok=True)
    # create a unique session id and place log file inside sessions folder
    import uuid, shutil

    session_id = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    log_basename = f"session_{session_id}.log"
    log_path = os.path.join(session_dir, log_basename)
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
            print("Unknown command. Type /help for commands.")
            continue

        # Send user input to agent and stream reply
        collected = ""
        try:
            for step in agent.stream({"messages": [{"role": "user", "content": user_input}]}):
                raw = str(step)
                collected += raw
                # Log full step (thinking) to file
                try:
                    logger.info(raw)
                except Exception:
                    pass
                # prefer AIMessage content if available
                content = getattr(step, "content", None) if hasattr(step, "content") else None
                if content is None and isinstance(step, dict):
                    content = step.get("content") or step.get("text")
                if content:
                    print(f"{AGENT_NAME}: {content}")
        except Exception as e:
            logger.exception("Agent stream error: %s", e)
            print("Agent stream error:", e)
            continue

        # Post-process concise answer
        concise = extract_answer(collected)
        print(f"{AGENT_NAME}: {concise}")
        history.append({"user": user_input, "ai": concise, "raw": collected})
        # Log concise answer
        try:
            logger.info("User: %s", user_input)
            logger.info("Concise: %s", concise)
        except Exception:
            pass
        # autosave session after each interaction
        try:
            with open(autosave_path, "w", encoding="utf-8") as fh:
                json.dump({"history": history, "session_id": session_id}, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _setup_logger(log_path="sessions/agent_thinking.log"):
    logger = logging.getLogger("agent_thinking")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

