import sys
import os
sys.path.append(os.path.abspath('backend'))
from app.engine.graphs.graph import get_interview_workflow

workflow = get_interview_workflow()
config = {"configurable": {"thread_id": "test_123"}}
initial_state = {
    "user_id": "test",
    "report_email": "test",
    "job_title": "AI Engineer",
    "experience": "신입",
    "education": "학사",
    "resume": "",
    "interview_mode": "short",
    "status": "PREPARING"
}
state = workflow.invoke(initial_state, config=config)
print("KEYS:", state.keys())
print("INSTRUCTIONS:", repr(state.get("realtime_instructions", "MISSING")))
