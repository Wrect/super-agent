import asyncio
import sys
import json

from agents.crew import get_omni_browser_agent
from browser.engine import close_browser_engine
from output.formatter import OutputFormatter

async def chat_loop():
    print("=" * 60)
    print("🤖 OMNI BROWSER AGENT - INTERACTIVE CHAT MODE")
    print("=" * 60)
    print("Type your commands in completely natural language, just like you would to me.")
    print("Type 'exit' or 'quit' to stop.")
    print("-" * 60 + "\n")
    
    agent = get_omni_browser_agent()
    formatter = OutputFormatter()
    
    try:
        while True:
            try:
                user_input = input("🗣️ You: ").strip()
            except EOFError:
                break
                
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye! 👋")
                break
                
            print(f"\n⚙️ Agent is executing: '{user_input}'...")
            
            try:
                # Execute the natural language task
                result = await agent.execute_task(user_input)
                
                # Format the output beautifully using your existing output formatter
                output = (
                    formatter.format_search_results([result])
                    if isinstance(result, dict) and "results" in result
                    else json.dumps(result, indent=2, default=str)
                )
                print(f"\n✅ Finished processing!")
                print(output)
                print("\n" + "-" * 60)
                
            except Exception as e:
                print(f"❌ Error executing task: {str(e)}")
                print("-" * 60 + "\n")
                
    finally:
        # Guarantee browser cleanup when exiting
        print("Cleaning up browser engines...")
        await close_browser_engine()


if __name__ == "__main__":
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nProcess interrupted. Cleaning up and exiting...")
        # Since we can't await in a synchronous except block easily without creating a new loop,
        # we rely on the clean up being fine or letting the OS kill the child processes.
        # But for neatness:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(close_browser_engine())
            else:
                loop.run_until_complete(close_browser_engine())
        except Exception:
            pass
        print("Goodbye!")
