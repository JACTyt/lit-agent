from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from agent.tools import toolbox
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware

import os
from dotenv import load_dotenv

load_dotenv()

# Friendly agent name
AGENT_NAME = os.getenv("AGENT_NAME", "LitBot")

# System prompt tuned for multi-turn, session-style chat grounded in local books
SYSTEM_PROMPT = (
    f"You are {AGENT_NAME}, a helpful literature research assistant with access to a local book database."
    " Answer user questions only using the ingested books and their retrieved passages. Be concise, cite sources when relevant, and keep replies suitable for conversational display."
    " If you use a tool, clearly indicate the tool name and summarize the result in one short paragraph."
)

llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

# Configure tool-call limits to avoid infinite cycling:
# - Per-tool thread limit (default 3): prevents any single tool from being
#   executed more than this number of times across the session/thread.
# - Global run/thread limit (default 10): caps total tool calls.
PER_TOOL_THREAD_LIMIT = int(os.getenv("PER_TOOL_THREAD_LIMIT", "3"))
GLOBAL_TOOL_LIMIT = int(os.getenv("GLOBAL_TOOL_LIMIT", "10"))

middleware = [
    ToolCallLimitMiddleware(tool_name="GetContext", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="Summarize", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="MoralCreator", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    # Global limiter for total tool calls per run/thread
    ToolCallLimitMiddleware(thread_limit=GLOBAL_TOOL_LIMIT, run_limit=GLOBAL_TOOL_LIMIT, exit_behavior="continue"),
]

agent = create_agent(
    model=llm,
    tools=toolbox,
    system_prompt=SYSTEM_PROMPT,
    middleware=middleware,
)

def init_agent():
    return agent
