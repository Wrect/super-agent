import asyncio
from agents.crew import get_omni_browser_agent
from browser.engine import close_browser_engine

async def main():
    agent = get_omni_browser_agent()
    print("Agent initialized. Running Instagram task...")
    result = await agent.execute_task(
        "open instagram and go to the saved gallery to download only one video at 7 number from top to bottom"
    )
    print("\n=== RESULT ===")
    import json
    print(json.dumps(result, indent=2, default=str))
    await close_browser_engine()

if __name__ == "__main__":
    asyncio.run(main())
