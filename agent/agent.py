from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from agent.tools import toolbox

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

agent = create_agent(
    model=llm,
    tools=toolbox,
    system_prompt=SYSTEM_PROMPT,
)

def init_agent():
    return agent
