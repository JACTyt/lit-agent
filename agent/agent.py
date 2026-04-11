from langchain.agents import create_agent
from langchain.tools import tool
from agent.tools import toolbox
from agent.llm_provider import get_chat_llm
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
    " Your job is to act like a careful librarian: classify books consistently, recommend useful organization schemes, summarize plots accurately, create original stories, and explain a book's motivation, moral, or lesson when asked."
    " When the user asks to create, read, update, or rename a book, use the library management tools and keep every file operation inside library/."
    " For any user request that asks to create, generate, write, or save a story/book, you MUST call CreateBook before giving a final answer."
    " Do not return a chat-only story for creation requests; first persist via CreateBook, then report the saved file path and short confirmation."
    " For story creation, it is acceptable to use more than one API call: first draft an outline or parts plan, then generate the story in sections, then assemble and refine the final narrative."
    " When the user asks for classification, use the ClassifyBook tool and present the result as structured metadata."
    " Use only the ingested books and retrieved passages as your evidence when answering book-specific questions. If the context is insufficient, say so clearly instead of guessing."
    " When classifying or organizing a book, prefer stable categories such as genre, theme, audience/reading level, and author, and explain the reasoning behind the chosen category briefly."
    " When summarizing, keep the response concise, factual, and source-grounded. When extracting a moral or lesson, give the answer in one short paragraph and include the supporting idea from the text."
    " If you use a tool, clearly indicate the tool name and summarize the result in one short paragraph."
    " Maintain consistent terminology across the session so repeated requests for the same book produce the same category and framing whenever the evidence is unchanged."
    "\n\nUse the following librarian reference notes as the domain knowledge source:\n"
    f"{DOMAIN_KNOWLEDGE if DOMAIN_KNOWLEDGE else 'No domain knowledge files were found.'}"
)

llm = get_chat_llm(temperature=0)

# Configure tool-call limits to avoid infinite cycling:
# - Per-tool thread limit (default 3): prevents any single tool from being
#   executed more than this number of times across the session/thread.
# - Global run/thread limit (default 10): caps total tool calls.
PER_TOOL_THREAD_LIMIT = int(os.getenv("PER_TOOL_THREAD_LIMIT", "3"))
GLOBAL_TOOL_LIMIT = int(os.getenv("GLOBAL_TOOL_LIMIT", "10"))

middleware = [
    ToolCallLimitMiddleware(tool_name="CreateBook", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="ReadBook", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="UpdateBookMetadata", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="RenameBook", thread_limit=PER_TOOL_THREAD_LIMIT, exit_behavior="continue"),
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
