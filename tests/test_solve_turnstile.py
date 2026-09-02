"""Tests for playwright-turnstile.

No real Playwright browser and no live Peak key are required. Peak's HTTP layer
is mocked, and a fake async ``page`` implements only the methods the helper
calls. Run: ``python -m unittest discover -s tests -v`` (or ``python -m pytest``).
"""

import io
import json
import os
import sys
import unittest
from unittest import mock

# Make ``src`` importable without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from playwright_turnstile import PeakError, solve_turnstile, solve_turnstile_sync  # noqa: E402
from playwright_turnstile import _peak  # noqa: E402
from playwright_turnstile._peak import build_solve_body  # noqa: E402

SAMPLE_SITEKEY = "0x4AAAAAAABkMYinukE8nzYS"
SAMPLE_URL = "https://protected.example/login"
TEST_TOKEN = "XXXX.TEST"


class FakeElement:
    """Stand-in for a Playwright ElementHandle."""

    def __init__(self, attrs):
        self._attrs = attrs

    async def get_attribute(self, name):
        return self._attrs.get(name)


class FakePage:
    """Async fake of a Playwright Page exposing only what the helper uses."""

    def __init__(self, sitekey=SAMPLE_SITEKEY, url=SAMPLE_URL):
        self.url = url
        self._sitekey = sitekey
        self.query_selector_calls = []
        self.evaluate_calls = []  # list of (js, arg)

    async def query_selector(self, selector):
        self.query_selector_calls.append(selector)
        if self._sitekey and "data-sitekey" in selector:
            return FakeElement({"data-sitekey": self._sitekey})
        return None

    async def evaluate(self, js, *args):
        self.evaluate_calls.append((js, args[0] if args else None))
        # Emulate the in-page injection return value.
        if "cf-turnstile-response" in js:
            return {"injected": True, "callbackInvoked": True}
        # Emulate the sitekey-scrape fallback.
        return self._sitekey


def make_urlopen(captured, response=None):
    """Build a fake urlopen that records the request and returns a canned body."""
    if response is None:
        response = {"success": True, "data": {"token": TEST_TOKEN}, "cost": 0.001}
    payload = json.dumps(response).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return io.BytesIO(payload)

    return fake_urlopen


class SolveBodyTests(unittest.TestCase):
    def test_body_omits_proxy_when_absent(self):
        body = build_solve_body(SAMPLE_SITEKEY, SAMPLE_URL)
        self.assertEqual(
            body,
            {"task_type": "turnstiletask", "sitekey": SAMPLE_SITEKEY, "url": SAMPLE_URL},
        )
        self.assertNotIn("proxy", body)

    def test_body_includes_proxy_when_given(self):
        body = build_solve_body(SAMPLE_SITEKEY, SAMPLE_URL, proxy="http://u:p@1.2.3.4:8000")
        self.assertEqual(body["proxy"], "http://u:p@1.2.3.4:8000")


class SolveTurnstileTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_sitekey_calls_peak_and_injects_token(self):
        page = FakePage()
        captured = {}

        with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured)):
            token = await solve_turnstile(page, api_key="pk_test_key")

        # Token returned.
        self.assertEqual(token, TEST_TOKEN)

        # Sitekey was read from the DOM widget.
        self.assertTrue(
            any("data-sitekey" in sel for sel in page.query_selector_calls),
            "helper never queried a [data-sitekey] widget",
        )

        # Peak was called with the correct endpoint, method, header and body.
        self.assertEqual(captured["url"], "https://api.peak.fo/solve")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"].get("x-api-key"), "pk_test_key")
        self.assertEqual(
            captured["body"],
            {
                "task_type": "turnstiletask",
                "sitekey": SAMPLE_SITEKEY,
                "url": SAMPLE_URL,
            },
        )

        # Token was injected via a page.evaluate call carrying the token + JS.
        inject_calls = [
            (js, arg) for (js, arg) in page.evaluate_calls if "cf-turnstile-response" in js
        ]
        self.assertEqual(len(inject_calls), 1, "expected exactly one injection evaluate call")
        inject_js, inject_arg = inject_calls[0]
        self.assertEqual(inject_arg, TEST_TOKEN)
        self.assertIn("data-callback", inject_js)  # fires the widget success callback

    async def test_proxy_is_forwarded_to_peak(self):
        page = FakePage()
        captured = {}
        with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured)):
            await solve_turnstile(page, api_key="pk_test_key", proxy="http://u:p@1.2.3.4:8000")
        self.assertEqual(captured["body"]["proxy"], "http://u:p@1.2.3.4:8000")

    async def test_explicit_sitekey_skips_dom_read(self):
        page = FakePage(sitekey=None)  # DOM has no widget
        captured = {}
        with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured)):
            token = await solve_turnstile(page, api_key="pk_test_key", sitekey="0xEXPLICIT")
        self.assertEqual(token, TEST_TOKEN)
        self.assertEqual(captured["body"]["sitekey"], "0xEXPLICIT")

    async def test_missing_sitekey_raises(self):
        page = FakePage(sitekey=None)
        with self.assertRaises(PeakError):
            await solve_turnstile(page, api_key="pk_test_key")

    async def test_peak_failure_raises(self):
        page = FakePage()
        captured = {}
        fail = {"success": False, "error": "insufficient balance"}
        with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured, fail)):
            with self.assertRaises(PeakError) as ctx:
                await solve_turnstile(page, api_key="pk_test_key")
        self.assertIn("insufficient balance", str(ctx.exception))

    async def test_api_key_from_env(self):
        page = FakePage()
        captured = {}
        with mock.patch.dict(os.environ, {"PEAK_API_KEY": "pk_env_key"}):
            with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured)):
                await solve_turnstile(page)
        self.assertEqual(captured["headers"].get("x-api-key"), "pk_env_key")

    async def test_missing_api_key_raises(self):
        page = FakePage()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PeakError):
                await solve_turnstile(page)


class FakeSyncElement:
    def __init__(self, attrs):
        self._attrs = attrs

    def get_attribute(self, name):
        return self._attrs.get(name)


class FakeSyncPage:
    def __init__(self, sitekey=SAMPLE_SITEKEY, url=SAMPLE_URL):
        self.url = url
        self._sitekey = sitekey
        self.evaluate_calls = []

    def query_selector(self, selector):
        if self._sitekey and "data-sitekey" in selector:
            return FakeSyncElement({"data-sitekey": self._sitekey})
        return None

    def evaluate(self, js, *args):
        self.evaluate_calls.append((js, args[0] if args else None))
        if "cf-turnstile-response" in js:
            return {"injected": True, "callbackInvoked": True}
        return self._sitekey


class SolveTurnstileSyncTests(unittest.TestCase):
    def test_sync_wrapper_solves_and_injects(self):
        page = FakeSyncPage()
        captured = {}
        with mock.patch.object(_peak.urllib.request, "urlopen", make_urlopen(captured)):
            token = solve_turnstile_sync(page, api_key="pk_test_key")
        self.assertEqual(token, TEST_TOKEN)
        self.assertEqual(captured["body"]["sitekey"], SAMPLE_SITEKEY)
        inject_calls = [c for c in page.evaluate_calls if "cf-turnstile-response" in c[0]]
        self.assertEqual(len(inject_calls), 1)
        self.assertEqual(inject_calls[0][1], TEST_TOKEN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
