"""Async example: solve Turnstile on a protected page, then submit.

Run:
    pip install playwright-turnstile playwright
    playwright install chromium
    export PEAK_API_KEY=pk_your_api_key   # Windows: set PEAK_API_KEY=pk_your_api_key
    python async_example.py
"""

import asyncio
import os

from playwright.async_api import async_playwright

from playwright_turnstile import solve_turnstile

TARGET_URL = "https://protected.example/login"


async def main():
    api_key = os.environ.get("PEAK_API_KEY", "pk_your_api_key")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(TARGET_URL)

        # Solve the Turnstile challenge and inject the token.
        token = await solve_turnstile(page, api_key=api_key)
        print("Turnstile solved, token injected:", token[:24], "...")

        # The token is now in cf-turnstile-response and the widget callback has
        # fired, so a normal submit / navigation proceeds.
        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
