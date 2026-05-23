import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.agent import init_agent
from scripts.extract_answer import extract_answer

router = APIRouter()
_agent_instance = None
_run_store: dict[str, asyncio.Queue] = {}


def _get_agent():
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = init_agent()
    return _agent_instance


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _run_store[run_id] = queue

    async def _run():
        agent = _get_agent()
        collected = ""
        try:
            for step in agent.stream({"messages": [{"role": "user", "content": req.message}]}):
                raw = str(step)
                collected += raw
                if isinstance(step, dict):
                    for v in step.values():
                        if isinstance(v, dict):
                            msgs = v.get("messages", [])
                            for m in (msgs if isinstance(msgs, list) else [msgs]):
                                content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                                if content:
                                    for token in str(content).split():
                                        await queue.put(json.dumps({"type": "token", "text": token + " "}))
                                        await asyncio.sleep(0)
        except Exception as exc:
            await queue.put(json.dumps({"type": "token", "text": f"Error: {exc}"}))
        finally:
            reply = extract_answer(collected)
            await queue.put(json.dumps({"type": "done", "reply": reply}))
            await queue.put(None)  # sentinel

    asyncio.create_task(_run())
    return {"run_id": run_id, "status": "streaming"}


@router.get("/stream/{run_id}")
async def stream(run_id: str):
    queue = _run_store.get(run_id)
    if not queue:
        async def _not_found() -> AsyncGenerator:
            yield {"data": json.dumps({"type": "done", "reply": "Run not found"})}
        return EventSourceResponse(_not_found())

    async def _generate() -> AsyncGenerator:
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=120)
                if item is None:
                    break
                yield {"data": item}
        finally:
            _run_store.pop(run_id, None)

    return EventSourceResponse(_generate())
