import asyncio
import sys
import os
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Load Environment Variables
load_dotenv()

from app.engine.graphs.interview_graph import app
from app.core.database import db
from langchain_core.messages import HumanMessage, AIMessage

async def main():
    print("🚀 AI TechTree Interview Agent CLI (v1.1)")
    print("------------------------------------------")
    print("Testing 'interview_graph' interactive mode.\n")

    # 1. Initialize State
    # We use a dummy user_id for CLI testing
    initial_state = {
        "user_id": "test_user@ai-techtree.com", 
        "messages": [],
        "track": "Python",
        "topic": "General",
        "level": "Intermediate", 
        "question_count": 0,
        "max_questions": 5
    }
    
    # We need to maintain the 'messages' list manually if we simulate a long session,
    # but app.ainvoke usually returns the updated state with appended messages.
    # For LangGraph stateful run, we should re-feed the history or let the graph handle it if we use checkpointer.
    # Here, 'interview_graph' is compiled without a checkpointer, so it runs a single turn or chain of turns until it stops.
    # To simulate a continuous conversation, we need to pass the updated state back in.
    
    current_state = initial_state
    
    # 2. Conversation Loop
    while True:
        try:
            user_input = input("\n👤 User: ")
            if user_input.lower() in ["q", "quit", "exit"]:
                print("Bye!")
                break
                
            # Add user message to state
            # Note: LangGraph's 'add_messages' annotation handles appending, 
            # but when we invoke with a dict, we usually provide the *new* messages or the full history depending on config.
            # In this simple setup without persistence/checkpointer, we have to pass the accumulating list?
            # Actually, let's try passing just the new message and let the graph logic handle it?
            # 'interview_graph.py' uses 'add_messages', so we should pass the list.
            
            # Update messages in current_state manually before invoke?
            # Or just pass the new message in the input?
            # Let's just pass the updated messages list.
            
            if "messages" not in current_state:
                current_state["messages"] = []
                
            current_state["messages"].append(HumanMessage(content=user_input))
            
            print("🤖 Agent is thinking...", end="", flush=True)
            
            # 3. Run Graph
            # We use 'invoke' which runs until the graph hits END or an interrupt.
            async for event in app.astream(current_state):
                # event is a dict of node_name -> output_state_update
                for node_name, state_update in event.items():
                    # Update our local current_state with the updates
                    # This implies we merge the dicts.
                    # Note: 'messages' in state_update are usually just the NEW messages added by that node.
                    # We need to be careful not to duplicate if we just blindly merge.
                    # But for CLI display, we just want to show the latest AIMessage.
                    
                    if "messages" in state_update:
                        new_msgs = state_update["messages"]
                        if new_msgs:
                            last_msg = new_msgs[-1]
                            if isinstance(last_msg, AIMessage):
                                print(f"\r🤖 Agent ({node_name}): {last_msg.content}")
                                
                                # Append to our local state to keep memory for next turn
                                # (In a real app, checkpointer manages this)
                                # current_state["messages"].append(last_msg) 
                    
                    # Merge other keys (user_db_id, topic, etc.)
                    current_state.update(state_update)

            # Manual fix for messages list to avoid duplication if the graph returned full list
            # Actually, app.invoke returns the FINAL state. app.astream yields updates.
            # Let's verify what 'current_state' holds after the loop.
            # The 'state_update' from astream usually contains only the diffs or the node output.
            
            # To be safe and simple for CLI:
            # Let's rely on the graph's final output for the next turn's input context?
            # BUT without checkpointer, the graph instance is stateless.
            # We MUST provide the full history in 'messages' every time we call it.
            
            # The 'astream' loop updated 'current_state' via my manual merge.
            # 'state_update["messages"]' from add_messages annotated nodes usually returns the list of NEW messages.
            # So appending them to current_state["messages"] is correct.
            
            # Let's handle the message append logic more robustly inside the loop.
            # If the node output 'messages' contains only the new ones, we append.
            # If it contains all, we replace.
            # LangGraph 'add_messages' reducer logic makes the *state* contain all, 
            # but the *node return* is usually what the node function returned.
            # In my graph, nodes return {"messages": [AIMessage(...)]}.
            # So the node output is just the new message.
            
            pass 

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
