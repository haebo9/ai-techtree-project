
import asyncio
import sys
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# 1. Setup Paths
# Current script is in backend/test_agent_db.py
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = current_dir # backend/
sys.path.append(backend_root)

# Internal agent src path for 'from agent import ...'
agent_src_path = os.path.join(backend_root, "app/engine/agents/langgraph/src")
sys.path.append(agent_src_path)

# Load Env
load_dotenv(os.path.join(backend_root, ".env"))

# Import Agent Graph
from agent.graph import graph

async def main():
    print("--- Starting Agent Test (v1.1 with Real DB) ---")
    
    # Simulate a user starting an interview on "Python"
    inputs = {
        "messages": [HumanMessage(content="파이썬 면접 시작할래")],
        "user_id": "test_runner_user",
        "topic": "Python"
    }
    
    config = {"configurable": {"thread_id": "test_thread_db_1"}}
    
    print(f"User Input: {inputs['messages'][0].content}")
    print("-" * 50)
    
    async for event in graph.astream(inputs, config=config):
        for node_name, state_update in event.items():
            print(f"\n📍 Node: {node_name}")
            
            # Print Key Updates
            if "user_intent" in state_update:
                print(f"   -> Intent: {state_update['user_intent']}")
            
            if "messages" in state_update:
                last_msg = state_update["messages"][-1]
                print(f"   -> Agent Message: {last_msg.content[:100]}...")
            
            if "current_question" in state_update:
                q = state_update["current_question"]
                print(f"   -> Question Ready: {q.get('question_text')}")

if __name__ == "__main__":
    asyncio.run(main())
