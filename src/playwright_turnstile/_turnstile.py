"""Turnstile-first Playwright helper.

Reads the Turnstile sitekey from the page, sends it to Peak for a token, then
injects the token so submit/navigation proceeds without a headless click.
"""

from __future__ import annotations

import asyncio

from ._peak import PeakError, request_token

# Selectors that Cloudflare's Turnstile widget renders into the page.
_WIDGET_SELECTORS = (
    ".cf-turnstile[data-sitekey]",
    "[data-sitekey]",
    "iframe[src*='challenges.cloudflare.com']",
)

# JS run in the page to scrape a sitekey when no element handle carries it as an
# attribute (implicit rendering, iframe-only widgets, turnstile.render config).
_FIND_SITEKEY_JS = """() => {
  const el = document.querySelector('[data-sitekey]');
  if (el) return el.getAttribute('data-sitekey');
  const frame = document.querySelector("iframe[src*='challenges.cloudflare.com']");
  if (frame) {
    const m = frame.getAttribute('src').match(/[?&]sitekey=([^&]+)/);
    if (m) return decodeURIComponent(m[1]);
  }
  return null;
}"""

# JS run in the page to inject the solved token. Sets every Turnstile / reCAPTCHA
# style response field, creating a hidden input if the widget has not made one
# yet, then fires the widget's success callback so the host page's handler runs.
_INJECT_TOKEN_JS = """(token) => {
  const names = ['cf-turnstile-response', 'g-recaptcha-response'];
  const setField = (name) => {
    let fields = Array.from(document.querySelectorAll(
      `[name="${name}"], #${name.replace(/[^a-zA-Z0-9_-]/g, '')}`
    ));
    if (fields.length === 0) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = name;
      const form = document.querySelector('form');
      (form || document.body).appendChild(input);
      fields = [input];
    }
    for (const f of fields) {
      f.value = token;
      f.dispatchEvent(new Event('input', { bubbles: true }));
      f.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };
  names.forEach(setField);

  let called = false;
  const widget = document.querySelector('.cf-turnstile[data-callback], [data-callback]');
  if (widget) {
    const cbName = widget.getAttribute('data-callback');
    if (cbName && typeof window[cbName] === 'function') {
      try { window[cbName](token); called = true; } catch (e) {}
    }
  }
  return { injected: true, callbackInvoked: called };
}"""


async def _read_sitekey(page) -> str | None:
    """Read the Turnstile sitekey from the widget in the DOM."""
    for selector in _WIDGET_SELECTORS:
        element = await page.query_selector(selector)
        if element is None:
            continue
        try:
            sitekey = await element.get_attribute("data-sitekey")
        except Exception:
            sitekey = None
        if sitekey:
            return sitekey
    # Fallback: scrape it in-page (covers iframe src / implicit render).
    return await page.evaluate(_FIND_SITEKEY_JS)


async def solve_turnstile(
    page,
    api_key: str | None = None,
    proxy: str | None = None,
    sitekey: str | None = None,
    timeout: float = 180.0,
) -> str:
    """Solve the Cloudflare Turnstile challenge on ``page`` via Peak.

    Reads the sitekey from the page (unless one is passed), asks Peak for a
    token, then injects that token and fires the widget callback so the page's
    submit/navigation can proceed.

    Args:
        page: A Playwright async ``Page`` sitting on a Turnstile-protected page.
        api_key: Peak API key. Falls back to the ``PEAK_API_KEY`` env var.
        proxy: Optional proxy string passed to Peak, e.g.
            ``http://user:pass@ip:port``. Use the same egress IP as the browser.
        sitekey: Override the sitekey instead of reading it from the DOM.
        timeout: Seconds to wait for Peak to return a token.

    Returns:
        The solved Turnstile token (also injected into the page).

    Raises:
        PeakError: if no sitekey is found, or Peak fails to solve.
    """
    if sitekey is None:
        sitekey = await _read_sitekey(page)
    if not sitekey:
        raise PeakError(
            "No Turnstile sitekey found on the page. Is the widget loaded? "
            "You can pass sitekey=... explicitly."
        )

    url = page.url

    token = await asyncio.to_thread(
        request_token,
        sitekey,
        url,
        api_key=api_key,
        proxy=proxy,
        timeout=timeout,
    )

    await page.evaluate(_INJECT_TOKEN_JS, token)
    return token


def solve_turnstile_sync(
    page,
    api_key: str | None = None,
    proxy: str | None = None,
    sitekey: str | None = None,
    timeout: float = 180.0,
) -> str:
    """Blocking convenience wrapper around Turnstile solving for the sync API.

    Use this with Playwright's *sync* API (``sync_playwright``), where ``page``
    methods return values directly instead of awaitables.
    """
    if sitekey is None:
        sitekey = _read_sitekey_sync(page)
    if not sitekey:
        raise PeakError(
            "No Turnstile sitekey found on the page. Is the widget loaded? "
            "You can pass sitekey=... explicitly."
        )

    token = request_token(
        sitekey,
        page.url,
        api_key=api_key,
        proxy=proxy,
        timeout=timeout,
    )
    page.evaluate(_INJECT_TOKEN_JS, token)
    return token


def _read_sitekey_sync(page) -> str | None:
    for selector in _WIDGET_SELECTORS:
        element = page.query_selector(selector)
        if element is None:
            continue
        try:
            sitekey = element.get_attribute("data-sitekey")
        except Exception:
            sitekey = None
        if sitekey:
            return sitekey
    return page.evaluate(_FIND_SITEKEY_JS)
