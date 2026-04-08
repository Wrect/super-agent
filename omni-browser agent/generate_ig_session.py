import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

async def generate_session():
    print("Starting Chromium for Instagram Session Generation...")
    async with async_playwright() as p:
        # Launch using your locally installed Google Chrome
        browser = await p.chromium.launch(headless=False, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to Instagram...")
        await page.goto("https://www.instagram.com/accounts/login/")
        
        print("\n" + "="*50)
        print("👉 Please log in to Instagram in the opened browser window.")
        print("👉 Once you have successfully logged in and can see your feed,")
        input("👉 Press ENTER in this console to save the session...")
        print("="*50 + "\n")
        
        print("Extracting session cookies...")
        cookies = await context.cookies()
        
        # Search for the sessionid cookie which identifies an IG session
        sessionid = next((c['value'] for c in cookies if c['name'] == 'sessionid'), "unknown_session")
        
        # Save to the structure expected by the AuthManager
        session_data = {
            "session_id": sessionid,
            "cookies": cookies,
            "expires_at": time.time() + (30 * 24 * 60 * 60) # 30 days
        }
        
        tokens_dir = Path("data/tokens")
        tokens_dir.mkdir(parents=True, exist_ok=True)
        
        target_file = tokens_dir / "instagram_session.json"
        with open(target_file, "w") as f:
            json.dump(session_data, f, indent=2)
            
        print(f"✅ SUCCESS! Instagram session successfully captured and saved to {target_file}")
        
        await browser.close()
        
        # Optional: Clean up temp profile
        # shutil.rmtree(user_data_dir)

if __name__ == "__main__":
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\nProcess cancelled by user.")
