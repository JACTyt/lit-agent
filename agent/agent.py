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


def _load_domain_knowledge(domain_knowledge_dir: str = "domain_knowledge") -> str:
    """Load compact librarian reference docs into the system prompt.

    The docs are intentionally stored in a separate folder so they can act as a
    small domain knowledge base without mixing with source books.
    """
    if not os.path.isdir(domain_knowledge_dir):
        return ""

    sections = []
    for filename in sorted(os.listdir(domain_knowledge_dir)):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(domain_knowledge_dir, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
            if content:
                sections.append(f"## {filename}\n{content}")
        except Exception:
            continue

    return "\n\n".join(sections)


DOMAIN_KNOWLEDGE = _load_domain_knowledge()

# System prompt tuned for multi-turn, session-style chat grounded in local books
SYSTEM_PROMPT = (
    f"You are {AGENT_NAME}, a librarian-domain expert and virtual library assistant with access to a local book database."
    " Your job is to act like a careful librarian: classify books consistently, recommend useful organization schemes, summarize plots accurately, and explain a book's motivation, moral, or lesson when asked."
    " When the user asks for classification, use the ClassifyBook tool and present the result as structured metadata."
    " Use only the ingested books and retrieved passages as your evidence when answering book-specific questions. If the context is insufficient, say so clearly instead of guessing."
    " When classifying or organizing a book, prefer stable categories such as genre, theme, audience/reading level, and author, and explain the reasoning behind the chosen category briefly."
    " When summarizing, keep the response concise, factual, and source-grounded. When extracting a moral or lesson, give the answer in one short paragraph and include the supporting idea from the text."
    " If you use a tool, clearly indicate the tool name and summarize the result in one short paragraph."
    " Maintain consistent terminology across the session so repeated requests for the same book produce the same category and framing whenever the evidence is unchanged."
    "\n\nUse the following librarian reference notes as the domain knowledge source:\n"
    f"{DOMAIN_KNOWLEDGE if DOMAIN_KNOWLEDGE else 'No domain knowledge files were found.'}"
)

llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

# Configure tool-call limits to avoid infinite cycling:
# - Per-tool thread limit (default 3): prevents any single tool from being
#   executed more than this number of times across the session/thread.
# - Global run/thread limit (default 10): caps total tool calls.
PER_TOOL_THREAD_LIMIT = int(os.getenv("PER_TOOL_THREAD_LIMIT", "3"))
GLOBAL_TOOL_LIMIT = int(os.getenv("GLOBAL_TOOL_LIMIT", "10"))

middleware = [
    ToolCallLimitMiddleware(tool_name="ClassifyBook", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
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
