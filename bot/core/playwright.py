"""Playwright-based fallback fetcher."""

# Standard library imports
import asyncio
import json as _json
import random
from concurrent.futures import ThreadPoolExecutor
import io
import os
import shutil
import tempfile

# Third party imports
from playwright.async_api import async_playwright
import aiohttp

# Local application imports
from bot.core.logger import log_error, log_warning, log_function, log_info


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


async def _get_random_public_proxy_option() -> dict:
    """
    Fetch a random public HTTP proxy from multiple sources. Returns Playwright
    proxy options dict: {"server": "http://host:port"} or None if unavailable.
    """
    sources = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=all",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    ]

    proxies: list[str] = []

    async def fetch_text(url: str) -> str:
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={"Accept": "text/plain"}) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception:
            return ""
        return ""

    for url in sources:
        text = await fetch_text(url)
        if not text:
            continue
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            # Expect host:port or protocol://host:port
            if ":" not in candidate:
                continue
            if candidate.startswith("http://") or candidate.startswith("https://"):
                proxies.append(candidate)
            else:
                proxies.append(f"http://{candidate}")

    if not proxies:
        return None

    import random as _rnd
    proxy_url = _rnd.choice(proxies)
    return {"server": proxy_url}


async def _playwright_check_async(identifier: str, retrive_all: bool = False):
    target_url = (
        f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&_={random.randint(1000000000000, 1999999999999)}"
    )

    async with async_playwright() as p:
        raw_json = None

        # Always use a real browser context to better handle Cloudflare
        # Try with a random public proxy first; fall back to direct if launch fails
        proxy_options = await _get_random_public_proxy_option()
        browser = None
        last_error = None
        for attempt in range(2):
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    proxy=proxy_options if attempt == 0 else None,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                break
            except Exception as e:
                last_error = e
                if attempt == 0:
                    log_warning(f"Chromium launch failed with proxy, retrying without proxy: {e}")
        if browser is None:
            raise last_error or RuntimeError("Failed to launch Chromium")

        video_tmpdir = tempfile.mkdtemp(prefix="pwvideo_")
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Kiev",
            record_video_dir=video_tmpdir,
            record_video_size={"width": 1280, "height": 720},
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

        # For admin notify on error
        error_for_admin = False
        screenshot_bytes = None
        video_path = None

        # Check IP address first to verify proxy is working
        try:
            ip_check_resp = await page.goto("https://2ip.ua", wait_until="domcontentloaded", timeout=15000)
            if ip_check_resp and ip_check_resp.status == 200:
                try:
                    # Get the IP from 2ip.ua page
                    current_ip = await page.evaluate("""
                        () => {
                            const ipElement = document.querySelector('.ip') || 
                                            document.querySelector('[data-ip]') ||
                                            document.querySelector('#d_clip_button span');
                            return ipElement ? ipElement.textContent.trim() : 'Unknown';
                        }
                    """)
                    log_info(f"Current IP for session {identifier}: {current_ip}")
                except Exception as ip_err:
                    log_warning(f"Failed to extract IP from 2ip.ua: {ip_err}")
            else:
                log_warning(f"Failed to load 2ip.ua, status: {getattr(ip_check_resp, 'status', 'unknown')}")
        except Exception as ip_check_err:
            log_warning(f"IP check failed: {ip_check_err}")

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
                    error_for_admin = True
                    try:
                        # Click reveal button before screenshot to unhide IP address
                        btn = await page.query_selector('#cf-footer-ip-reveal')
                        if btn is not None:
                            await btn.click()
                            await asyncio.sleep(1)
                        screenshot_bytes = await page.screenshot(full_page=True)
                    except Exception:
                        screenshot_bytes = None
                else:
                    try:
                        raw_text = await resp.text()
                        raw_json = _json.loads(raw_text)
                    except Exception:
                        try:
                            text = await page.evaluate("() => document.body.innerText")
                            raw_json = _json.loads(text)
                        except Exception as json_fallback_err:
                            error_for_admin = True
                            log_error(
                                f"Failed to parse response as JSON for {identifier}",
                                exception=json_fallback_err,
                            )
        finally:
            # Retrieve video path after closing context (video is finalized on close)
            try:
                await context.close()
            except Exception:
                pass
            try:
                # After context close page.video.path() should be available
                if hasattr(page, "video") and page.video:
                    try:
                        video_path = await page.video.path()
                    except Exception:
                        video_path = None
            except Exception:
                video_path = None
            try:
                await browser.close()
            except Exception:
                pass

        # Notify admin if needed
        if error_for_admin:
            try:
                from aiogram import Bot, types
                from bot.core.config import settings

                token = getattr(settings, "TOKEN", None)
                admin_id = getattr(settings, "ADMIN_ID", None)
                if token and admin_id:
                    bot_tmp = Bot(token=token)
                    if screenshot_bytes:
                        photo_file = types.InputFile(io.BytesIO(screenshot_bytes), filename="playwright_error.png")
                        await bot_tmp.send_photo(chat_id=admin_id, photo=photo_file, caption=f"Playwright fetch failed for {target_url}")

                    if video_path and os.path.exists(video_path):
                        try:
                            with open(video_path, "rb") as vf:
                                video_bytes = vf.read()
                            video_file = types.InputFile(io.BytesIO(video_bytes), filename="playwright_error.webm")
                            await bot_tmp.send_video(chat_id=admin_id, video=video_file, caption="Playwright session video")
                        except Exception as video_err:
                            log_warning(f"Failed to send video to admin: {video_err}")
                        finally:
                            try:
                                os.remove(video_path)
                            except Exception:
                                pass

                    session = await bot_tmp.get_session()
                    await session.close()
            except Exception as notify_err:
                log_warning(f"Failed to notify admin: {notify_err}")
            finally:
                # Cleanup temp video directory after notify
                try:
                    shutil.rmtree(video_tmpdir, ignore_errors=True)
                except Exception:
                    pass
        else:
            # No error: cleanup temp directory
            try:
                shutil.rmtree(video_tmpdir, ignore_errors=True)
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
