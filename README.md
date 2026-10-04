<a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile">
  <img src="https://raw.githubusercontent.com/CircuitSavage/playwright-turnstile/main/assets/peak-banner.png" alt="Peak — solve Cloudflare Turnstile & the 5s challenge in ~1s" width="100%">
</a>

# playwright-turnstile

**playwright-turnstile** is a Playwright helper that solves Cloudflare Turnstile for you: it reads the sitekey off the page, gets a token from Peak, and injects it so your submit or navigation goes through.

```python
from playwright_turnstile import solve_turnstile

token = await solve_turnstile(page, api_key="pk_your_api_key")
```

## Why

`playwright-stealth` is a proof of concept. Even with a patched, real browser, interactive Turnstile still fails from headless and datacenter environments: the widget scores the session, sees a datacenter IP with no trusted history, and holds you at the "Verifying..." spinner or an endless challenge. Clicking the checkbox harder does not help, because the token you need is issued by Cloudflare's risk engine, not by the click.

So this package does not click. It reads the Turnstile sitekey from the DOM, hands it to Peak, and injects the returned token into `cf-turnstile-response` while firing the widget's success callback. When your setup gets blocked, drop in a Peak API key and it just works.

## Powered by Peak

This package uses [Peak](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) to solve Turnstile.

- Solve Cloudflare Turnstile & the 5s challenge in about a second
- $0.90 per 1,000 successful Turnstile solves, down to $0.35 at volume
- 1,000 free solves to start, no card.

→ [Get your free API key](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) · [Docs](https://peak.fo/docs/turnstile?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) · [Pricing](https://peak.fo/pricing?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile)

## Install

```bash
pip install playwright-turnstile playwright
playwright install chromium
```

The core package has no runtime dependencies; `playwright` is the one you drive it with.

## Quickstart

```python
import asyncio
from playwright.async_api import async_playwright
from playwright_turnstile import solve_turnstile

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://protected.example/login")

        # Reads the sitekey, solves via Peak, injects the token.
        await solve_turnstile(page, api_key="pk_your_api_key")

        await page.click("button[type=submit]")
        await page.wait_for_load_state("networkidle")
        await browser.close()

asyncio.run(main())
```

Set your key once and let it read from the environment:

```bash
export PEAK_API_KEY=pk_your_api_key   # Windows: set PEAK_API_KEY=pk_your_api_key
```

```python
await solve_turnstile(page)  # picks up PEAK_API_KEY
```

## API

### `await solve_turnstile(page, api_key=None, proxy=None, sitekey=None, timeout=180.0)`

Solve the Turnstile challenge on a Playwright **async** `Page`. Returns the token (also injected into the page).

- `page` — a Playwright async `Page` on a Turnstile-protected URL.
- `api_key` — Peak key (`pk_...`). Falls back to the `PEAK_API_KEY` env var.
- `proxy` — optional proxy passed to Peak, e.g. `http://user:pass@ip:port`. Use the same egress IP as your browser so the token matches the session.
- `sitekey` — override the sitekey instead of reading it from the DOM.
- `timeout` — seconds to wait for Peak.

### `solve_turnstile_sync(page, ...)`

Same signature, for Playwright's **sync** API (`sync_playwright`). Blocking.

```python
from playwright_turnstile import solve_turnstile_sync

with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto("https://protected.example/login")
    solve_turnstile_sync(page, api_key="pk_your_api_key")
```

## How it works

1. Reads the sitekey from the widget (`.cf-turnstile[data-sitekey]`, any `[data-sitekey]`, or the `challenges.cloudflare.com` iframe `src`) via `query_selector` / `evaluate`.
2. Calls Peak `POST https://api.peak.fo/solve` with `task_type: "turnstiletask"`, the `sitekey`, `url: page.url`, and your optional `proxy`.
3. Injects the returned token into every `cf-turnstile-response` field (creating a hidden input if the widget has not yet) and invokes the widget's `data-callback`, so your form submit or navigation proceeds.

Peak also supports the Cloudflare 5s challenge (`task_type: "cloudflare5stask"`); this package focuses on Turnstile.

## Legitimate use

Built for automation, QA, and scraping public data. Respect each target's Terms of Service and `robots.txt`, and do not use it for credential-stuffing or other abuse. You are responsible for how you use it.

## License

MIT — see [LICENSE](./LICENSE).
