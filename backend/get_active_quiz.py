import sys
import httpx

def get_active(thread_id):
    try:
        resp = httpx.get(f"http://127.0.0.1:2024/threads/{thread_id}/state")
        state = resp.json()
        print(state)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_active(sys.argv[1])
