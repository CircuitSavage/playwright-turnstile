<a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile">
  <img src="https://raw.githubusercontent.com/CircuitSavage/playwright-turnstile/main/assets/peak-banner.png" alt="Peak: solve Cloudflare Turnstile and the 5s challenge from headless browsers and datacenter IPs" width="100%">
</a>

# playwright-turnstile

**playwright-turnstile** is a Playwright helper that solves Cloudflare Turnstile for you: it reads the sitekey off the page, gets a token from Peak, and injects it so your submit or navigation goes through.

```python
from playwright_turnstile import solve_turnstile

token = await solve_turnstile(page, api_key="pk_your_api_key")
```

## Why

`playwright-stealth` is a proof of concept. Even with a patched, real browser, interactive Turnstile still fails from headless and datacenter environments: the widget scores the session, sees a datacenter IP with no trusted history, and holds you at the "Verifying..." spinner or an endless challenge. Clicking the checkbox harder does not help, because the token you need is issued by Cloudflare's risk engine, not by the click.

So this package does not click. It reads the Turnstile sitekey from the DOM, hands it to Peak, and injects the returned token into `cf-turnstile-response` while firing the widget's success callback. When your setup gets blocked, drop in a Peak API key and it works.

## Powered by Peak

This package uses [Peak](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) to solve Turnstile.

- Solves Cloudflare Turnstile and the 5s challenge, headless, from datacenter IPs
- $0.90 per 1,000 successful Turnstile solves, down to $0.35 at volume
- 1,000 free solves to start, no card.

→ [Get your free API key](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) · [Docs](https://peak.fo/docs/turnstile?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile) · [Pricing](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=playwright-turnstile#pricing)

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

- `page`: a Playwright async `Page` on a Turnstile-protected URL.
- `api_key`: Peak key (`pk_...`). Falls back to the `PEAK_API_KEY` env var.
- `proxy`: optional proxy passed to Peak, e.g. `http://user:pass@ip:port`. Use the same egress IP as your browser so the token matches the session.
- `sitekey`: override the sitekey instead of reading it from the DOM.
- `timeout`: seconds to wait for Peak.
- `app_id`: optional Peak app ID. Falls back to the `PEAK_APP_ID` env var. Earns you a share of each solve, see [Earn with your app ID](#earn-with-your-app-id).

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

## Earn with your app ID

Pass `app_id="app_your_id"` (or set the `PEAK_APP_ID` environment variable) to earn 5% of every solve routed through this package, paid as Peak solve credit. It is optional and does not change whether a solve succeeds or how fast it returns.

```python
await solve_turnstile(page, app_id="app_your_id")   # or: export PEAK_APP_ID=app_your_id
```

Create an app id at [peak.fo/dashboard/developer](https://peak.fo/dashboard/developer); details at [peak.fo/earn](https://peak.fo/earn).

## Troubleshooting

The failures people report with this package come down to the same four. Each has a longer write-up on the Peak blog.

- **`PeakError: No Turnstile sitekey found on the page`.** The widget had not rendered when `solve_turnstile` ran, or the site loads it from a script the DOM selectors never see. Wait for `.cf-turnstile` or the `challenges.cloudflare.com` iframe before you call it, or pass `sitekey=` by hand. [How to find a Cloudflare Turnstile sitekey](https://blog.peak.fo/how-to-find-a-cloudflare-turnstile-sitekey/) covers the DevTools route and the places sites hide it.
- **`cf-turnstile-response` is empty when your own code reads it.** You read the field before the solve returned, or the page re-rendered the widget after injection and wiped the hidden input. Await `solve_turnstile`, then submit in the same step. [cf-turnstile-response is empty](https://blog.peak.fo/cf-turnstile-response-empty/) lists the causes in order, and [the cf-turnstile-response token explained](https://blog.peak.fo/the-cf-turnstile-response-token-explained/) covers what the server does with the token once it arrives.
- **The page still answers 403 after the token lands.** That is a different wall. A Turnstile token satisfies a widget on a form. A 403 interstitial wants a `cf_clearance` cookie from the 5-second challenge, which is Peak's `cloudflare5stask`, not this package. [Turnstile token vs cookie](https://blog.peak.fo/cloudflare-turnstile-token-vs-cookie/) explains which one you need, and [Cloudflare Turnstile 403](https://blog.peak.fo/cloudflare-turnstile-403-scraper-fix/) walks through the fix.
- **The widget shows an error code** such as 110200, 300030 or 600010. [Cloudflare Turnstile error codes](https://blog.peak.fo/cloudflare-turnstile-error-codes/) groups them by what failed, from a domain missing on the sitekey's allowlist to a challenge run that died inside the iframe.

The full walkthrough for this stack, including why the `proxy` you pass to Peak should match the browser's egress IP, is [Turnstile in Playwright and Puppeteer](https://blog.peak.fo/handling-turnstile-in-playwright-and-puppeteer/) (also on [Hashnode](https://peakfo.hashnode.dev/handling-turnstile-in-playwright-and-puppeteer)).

## Related

Same pattern for other stacks: [patchright-turnstile](https://github.com/CircuitSavage/patchright-turnstile) · [camoufox-turnstile](https://github.com/CircuitSavage/camoufox-turnstile) · [puppeteer-extra-plugin-turnstile](https://github.com/CircuitSavage/puppeteer-extra-plugin-turnstile) · [selenium-turnstile](https://github.com/CircuitSavage/selenium-turnstile) · [nodriver-turnstile](https://github.com/CircuitSavage/nodriver-turnstile) · [crawlee-turnstile](https://github.com/CircuitSavage/crawlee-turnstile) · [browser-use-turnstile](https://github.com/CircuitSavage/browser-use-turnstile) · [scrapy-turnstile](https://github.com/CircuitSavage/scrapy-turnstile). Full list in [awesome-turnstile-solvers](https://github.com/CircuitSavage/awesome-turnstile-solvers).

If you want to know what the widget does before it hands out a token, [cloudflare-turnstile-reversed](https://github.com/CircuitSavage/cloudflare-turnstile-reversed) documents the challenge flow, the widget parameters and the fingerprinting it runs.

## Legitimate use

Built for automation, QA, and scraping public data. Respect each target's Terms of Service and `robots.txt`, and do not use it for credential-stuffing or other abuse. You are responsible for how you use it.

## License

MIT, see [LICENSE](./LICENSE).
