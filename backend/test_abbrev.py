import sys
import os
import asyncio

# Set up path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.engine.agents.quiz import generate_explanation_only

async def main():
    res = await generate_explanation_only("DP")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
