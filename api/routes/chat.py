import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.agent import init_agent

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
        try:
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": req.message}]},
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", "") or ""
                        if content:
                            await queue.put(json.dumps({"type": "token", "text": content}))
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name:
                        await queue.put(json.dumps({"type": "tool_call", "tool": tool_name}))
        except Exception as exc:
            await queue.put(json.dumps({"type": "token", "text": f"\n[Error: {exc}]"}))
        finally:
            await queue.put(json.dumps({"type": "done", "reply": ""}))
            await queue.put(None)

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
