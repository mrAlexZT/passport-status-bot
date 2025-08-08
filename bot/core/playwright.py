"""Playwright-based fallback fetcher."""

# Standard library imports
import asyncio
import json as _json
import random
from concurrent.futures import ThreadPoolExecutor

# Third party imports
from playwright.async_api import async_playwright

# Local application imports
from bot.core.logger import log_error, log_warning, log_function


async def _playwright_check_async(identifier: str, retrive_all: bool = False):
    target_url = (
        f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&rand={random.randint(10000, 1999999)}"
    )

    async with async_playwright() as p:
        raw_json = None

        # 1) Try lightweight request context first
        try:
            async with p.request.new_context() as request_context:
                response = await request_context.get(target_url)
                if response.ok:
                    try:
                        raw_json = await response.json()
                    except Exception as json_err:
                        log_warning(
                            f"Playwright request JSON parse failed for {target_url}: {json_err}"
                        )
                        raw_json = None
                else:
                    log_warning(
                        f"Playwright request to {target_url} returned status code {response.status}"
                    )
        except Exception as e:
            log_warning(f"Playwright request context failed for {identifier}: {e}")

        # 2) If request context failed, try real browser navigation
        if not raw_json:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                resp = await page.goto(target_url, wait_until="domcontentloaded")
                if not resp or resp.status != 200:
                    log_warning(
                        f"Playwright page.goto to {target_url} returned status code {getattr(resp, 'status', 'unknown')}"
                    )
                    return None
                try:
                    raw_json = await resp.json()
                except Exception:
                    # Fallback: parse text / page content as JSON
                    try:
                        text = await resp.text()
                        raw_json = _json.loads(text)
                    except Exception:
                        try:
                            text = await page.evaluate("() => document.body.innerText")
                            raw_json = _json.loads(text)
                        except Exception as json_fallback_err:
                            log_error(
                                f"Failed to parse response as JSON for {identifier}",
                                exception=json_fallback_err,
                            )
                            return None
            finally:
                try:
                    await context.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass

    if not raw_json or "StatusInfo" not in raw_json:
        return None

    parsed_json = raw_json["StatusInfo"]
    status_list = [
        {"status": status.get("StatusName"), "date": status.get("StatusDateUF")}
        for status in parsed_json
    ]

    if retrive_all:
        return status_list
    return [status_list[-1]] if status_list else None


@log_function("playwright_check")
def playwright_check(identifier: str, retrive_all: bool = False):
    """
    Run the async Playwright flow in a background thread to avoid the
    "Sync API inside asyncio loop" issue and keep a sync interface.
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(_playwright_check_async(identifier, retrive_all)))
            return future.result()
    except Exception as e:
        log_error(f"Playwright check failed for {identifier}", exception=e)
        return None
