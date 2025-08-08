"""Playwright-based fallback fetcher."""

# Standard library imports
import asyncio
import json as _json
import random
from concurrent.futures import ThreadPoolExecutor
import io

# Third party imports
from playwright.async_api import async_playwright

# Local application imports
from bot.core.logger import log_error, log_warning, log_function


async def _apply_stealth_to_context(context):
    """
    Apply basic stealth measures to defeat simple bot detection:
    - navigator.webdriver
    - plugins/languages/platform
    - WebGL vendor/renderer
    """
    await context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        // Languages
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        // Plugins length
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        // Platform
        Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        // WebGL vendor/renderer spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
          // UNMASKED_VENDOR_WEBGL
          if (parameter === 37445) { return 'Apple Inc.'; }
          // UNMASKED_RENDERER_WEBGL
          if (parameter === 37446) { return 'Apple M1'; }
          return getParameter.call(this, parameter);
        };
        // chrome.runtime spoof
        window.chrome = { runtime: {} };
        // hairline fix
        Object.defineProperty(window, 'devicePixelRatio', { get: () => 2 });
        // Permissions query spoof
        const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
        if (originalQuery) {
          window.navigator.permissions.query = (parameters) => (
            parameters && parameters.name === 'notifications'
              ? Promise.resolve({ state: Notification.permission })
              : originalQuery(parameters)
          );
        }
        """
    )


async def _playwright_check_async(identifier: str, retrive_all: bool = False):
    target_url = (
        f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&rand={random.randint(10000, 1999999)}"
    )

    async with async_playwright() as p:
        raw_json = None

        # Always use a real browser context to better handle Cloudflare
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Kiev",
        )
        await _apply_stealth_to_context(context)
        page = await context.new_page()
        await page.set_extra_http_headers(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://passport.mfa.gov.ua/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        try:
            resp = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            # Detect Cloudflare challenge markers
            needs_wait = False
            try:
                title = await page.title()
                content = await page.content()
                status = getattr(resp, "status", None)
                needs_wait = (
                    (status in (403, 503))
                    or ("Just a moment" in (title or ""))
                    or ("cf-browser-verification" in (content or ""))
                    or ("cf-chl-" in (content or ""))
                )
            except Exception:
                pass

            # Wait up to ~20s for Cloudflare to solve, watching for cf_clearance cookie
            if needs_wait:
                for _ in range(20):
                    await asyncio.sleep(1)
                    cookies = await context.cookies()
                    if any(c.get("name") == "cf_clearance" for c in cookies):
                        break
                # Reload after potential clearance
                resp = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            # Prefer fetching JSON via fetch() with cookies included
            try:
                raw_json = await page.evaluate(
                    "async (url) => { \n"
                    "  const r = await fetch(url, { credentials: 'include' }); \n"
                    "  if (!r.ok) throw new Error('Bad status: ' + r.status); \n"
                    "  return await r.json(); \n"
                    "}",
                    target_url,
                )
            except Exception as _:
                # Fallback to response body parsing
                if not resp or resp.status != 200:
                    # Capture screenshot and try to notify admin
                    try:
                        screenshot_bytes = await page.screenshot(full_page=True)
                        from aiogram import Bot, types
                        from bot.core.config import settings

                        token = getattr(settings, "TOKEN", None)
                        admin_id = getattr(settings, "ADMIN_ID", None)
                        if token and admin_id:
                            bot_tmp = Bot(token=token)
                            input_file = types.InputFile(io.BytesIO(screenshot_bytes), filename="playwright_error.png")
                            await bot_tmp.send_photo(chat_id=admin_id, photo=input_file, caption=f"Playwright fetch failed for {identifier}")
                            session = await bot_tmp.get_session()
                            await session.close()
                    except Exception as notify_err:
                        log_warning(f"Failed to notify admin with screenshot: {notify_err}")
                    return None

                try:
                    raw_text = await resp.text()
                    raw_json = _json.loads(raw_text)
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
