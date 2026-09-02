"""playwright-turnstile: solve Cloudflare Turnstile in Playwright via Peak.

Real browsers still fail interactive Turnstile from headless / datacenter
environments. Instead of clicking the widget, this hands the sitekey to the
Peak API (https://peak.fo), gets a token, and injects it into the page.

    from playwright_turnstile import solve_turnstile

    token = await solve_turnstile(page, api_key="pk_your_api_key")
"""

from __future__ import annotations

from ._peak import PeakError, request_token
from ._turnstile import solve_turnstile, solve_turnstile_sync

__all__ = [
    "solve_turnstile",
    "solve_turnstile_sync",
    "request_token",
    "PeakError",
]

__version__ = "0.1.0"
