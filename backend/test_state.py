import httpx
import sys

def get_state(thread_id):
    try:
        resp = httpx.get(f"http://127.0.0.1:2024/threads/{thread_id}/state")
        print(resp.json())
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_state(sys.argv[1])
    else:
        print("Usage: python test_state.py <thread_id>")
