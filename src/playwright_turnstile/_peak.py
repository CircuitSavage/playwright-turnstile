"""Thin client for the Peak solve API (https://peak.fo).

Uses only the standard library so the package stays dependency-light. The
blocking HTTP call is wrapped in a thread by the async helper so it never
stalls the Playwright event loop.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

PEAK_SOLVE_URL = "https://api.peak.fo/solve"
DEFAULT_TIMEOUT = 180.0


class PeakError(RuntimeError):
    """Raised when Peak returns an error or the request fails."""


def _resolve_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("PEAK_API_KEY")
    if not key:
        raise PeakError(
            "No Peak API key. Pass api_key=... or set the PEAK_API_KEY "
            "environment variable. Get a free key at "
            "https://peak.fo."
        )
    return key


def build_solve_body(
    sitekey: str,
    url: str,
    proxy: str | None = None,
    app_id: str | None = None,
) -> dict:
    """Build the JSON body for a Turnstile solve task."""
    body = {
        "task_type": "turnstiletask",
        "sitekey": sitekey,
        "url": url,
    }
    if proxy:
        body["proxy"] = proxy
    if app_id:
        body["appId"] = app_id
    return body


def request_token(
    sitekey: str,
    url: str,
    api_key: str | None = None,
    proxy: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    app_id: str | None = None,
) -> str:
    """Call Peak /solve for a Turnstile token. Blocking.

    Returns the solved token string, or raises PeakError. ``app_id`` (or the
    ``PEAK_APP_ID`` env var) earns you a share of each solve — see the README.
    """
    key = _resolve_api_key(api_key)
    app_id = app_id or os.environ.get("PEAK_APP_ID") or None
    body = build_solve_body(sitekey, url, proxy, app_id)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        PEAK_SOLVE_URL,
        data=data,
        method="POST",
        headers={
            "X-API-Key": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "playwright-turnstile/0.2.0 (+https://github.com/CircuitSavage/playwright-turnstile)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover - network path
        detail = exc.read().decode("utf-8", "replace")
        raise PeakError(f"Peak HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network path
        raise PeakError(f"Could not reach Peak: {exc.reason}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PeakError(f"Peak returned invalid JSON: {raw!r}") from exc

    if not payload.get("success"):
        raise PeakError(f"Peak solve failed: {payload.get('error', 'unknown error')}")

    token = (payload.get("data") or {}).get("token")
    if not token:
        raise PeakError(f"Peak response missing token: {payload!r}")
    return token
