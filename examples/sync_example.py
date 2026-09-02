"""Sync example using Playwright's synchronous API.

Run:
    pip install playwright-turnstile playwright
    playwright install chromium
    export PEAK_API_KEY=pk_your_api_key   # Windows: set PEAK_API_KEY=pk_your_api_key
    python sync_example.py
"""

import os

from playwright.sync_api import sync_playwright

from playwright_turnstile import solve_turnstile_sync

TARGET_URL = "https://protected.example/login"


def main():
    api_key = os.environ.get("PEAK_API_KEY", "pk_your_api_key")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET_URL)

        # Optionally pass a proxy so Peak solves from the same egress IP:
        #   solve_turnstile_sync(page, api_key=api_key, proxy="http://user:pass@ip:port")
        token = solve_turnstile_sync(page, api_key=api_key)
        print("Turnstile solved, token injected:", token[:24], "...")

        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")

        browser.close()


if __name__ == "__main__":
    main()
