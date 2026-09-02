# Testing

The suite uses only the standard library: `unittest` + `unittest.mock`, with
`IsolatedAsyncioTestCase` for the async helper. No real Playwright browser and
no live Peak key are needed.

- Peak's HTTP layer is mocked at `playwright_turnstile._peak.urllib.request.urlopen`,
  returning `{"success": true, "data": {"token": "XXXX.TEST"}}`.
- A fake async `page` (`FakePage`) implements only the methods the helper calls:
  `url`, `query_selector` (returns a fake element exposing `get_attribute`), and
  `evaluate`. A separate `FakeSyncPage` covers the sync wrapper.

## What is asserted

- The sitekey is read from the `[data-sitekey]` widget in the DOM.
- Peak is called with the correct endpoint (`https://api.peak.fo/solve`),
  method (`POST`), header (`X-API-Key`), and body
  (`{"task_type": "turnstiletask", "sitekey": ..., "url": ...}`).
- The solved token is injected via exactly one `page.evaluate` call that carries
  the token and the `cf-turnstile-response` injection JS.
- `proxy` is forwarded when given and omitted when not.
- An explicit `sitekey=` skips the DOM read.
- Missing sitekey, missing API key, and a Peak `success: false` response each
  raise `PeakError`.
- `PEAK_API_KEY` is read from the environment when `api_key` is not passed.
- The sync wrapper (`solve_turnstile_sync`) solves and injects the same way.

## Run

```bash
python -m unittest discover -s tests -v
```

Python 3.12 (`python`). No third-party packages required.

## Observed output

```
$ python --version
Python 3.12.0

$ python -m unittest discover -s tests -v
test_body_includes_proxy_when_given (test_solve_turnstile.SolveBodyTests.test_body_includes_proxy_when_given) ... ok
test_body_omits_proxy_when_absent (test_solve_turnstile.SolveBodyTests.test_body_omits_proxy_when_absent) ... ok
test_sync_wrapper_solves_and_injects (test_solve_turnstile.SolveTurnstileSyncTests.test_sync_wrapper_solves_and_injects) ... ok
test_api_key_from_env (test_solve_turnstile.SolveTurnstileTests.test_api_key_from_env) ... ok
test_explicit_sitekey_skips_dom_read (test_solve_turnstile.SolveTurnstileTests.test_explicit_sitekey_skips_dom_read) ... ok
test_missing_api_key_raises (test_solve_turnstile.SolveTurnstileTests.test_missing_api_key_raises) ... ok
test_missing_sitekey_raises (test_solve_turnstile.SolveTurnstileTests.test_missing_sitekey_raises) ... ok
test_peak_failure_raises (test_solve_turnstile.SolveTurnstileTests.test_peak_failure_raises) ... ok
test_proxy_is_forwarded_to_peak (test_solve_turnstile.SolveTurnstileTests.test_proxy_is_forwarded_to_peak) ... ok
test_reads_sitekey_calls_peak_and_injects_token (test_solve_turnstile.SolveTurnstileTests.test_reads_sitekey_calls_peak_and_injects_token) ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.077s

OK
```
