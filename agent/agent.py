from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from agent.tools import toolbox

import os
from dotenv import load_dotenv, dotenv_values 

load_dotenv()

@tool("calculator", description="Performs arithmetic calculations. Use this for any math problems.")
def calculator(expression: str) -> str:
    return str(eval(expression))

tools = [ calculator]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,api_key=os.getenv("OPENAI_API_KEY"))

agent = create_agent(
    model=llm, 
    tools=toolbox,
    system_prompt="You are the local book storage. Dont lookup a books from internet, provide answers based on books stored. In the end of answer say: 'Nya!'",
)

def init_agent():
    return agent
