from agent.agent import init_agent

agent = init_agent()
"""
response = agent.invoke(
    {"messages": [{"role": "user", "content": "Find the book about flowers"}]}    
)

print(response)
"""
for step in agent.stream(
    {"messages": [{"role": "user", "content": "Tell me about rose from book The Proud Rose"}]}
):
    print(step)

for step in agent.stream(
    {"messages": [{"role": "user", "content": "Tell me about why ants where surprised in book The Ant and the Grasshopper"}]}
):
    print(step)
