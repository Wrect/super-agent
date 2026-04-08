import asyncio
import json
from auth.manager import get_auth_manager

async def test_auth():
    print("Initializing Auth Manager...")
    manager = get_auth_manager()
    
    # Check Instagram Auth Status
    print("\nRequesting Instagram session status...")
    status = await manager.get_auth_status()
    
    print(f"\nFinal Status Check:")
    print(json.dumps(status['instagram'], indent=2))
    
    if status['instagram']['authenticated']:
        print("\n✅ SUCCESS: The agent has successfully located and loaded the instagram_session.json file!")
    else:
        print("\n❌ FAILED: The agent did not recognize the instagram session.")

if __name__ == "__main__":
    asyncio.run(test_auth())
