# Standard library imports
import random

# Third party imports
from playwright.sync_api import sync_playwright

# Local application imports
from bot.core.logger import log_error, log_warning, log_function


@log_function("playwright_check")
def playwright_check(identifier: str, retrive_all: bool = False):
    """
    Fetch status data using Playwright. Provides a synchronous API compatible with existing code.

    Returns:
        list[dict] or None
    """
    target_url = (
        f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&rand={random.randint(10000, 1999999)}"
    )

    try:
        with sync_playwright() as p:
            # Prefer lightweight request context first
            request_context = p.request.new_context()
            try:
                response = request_context.get(target_url)
                if response.ok:
                    try:
                        raw_json = response.json()
                    except Exception as json_err:
                        log_warning(
                            f"Playwright request JSON parse failed for {target_url}: {json_err}"
                        )
                        raw_json = None
                else:
                    log_warning(
                        f"Playwright request to {target_url} returned status code {response.status}"
                    )
                    raw_json = None
            finally:
                request_context.dispose()

            # If request context failed (e.g., Cloudflare), try full browser navigation
            if not raw_json:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context()
                    page = context.new_page()
                    resp = page.goto(target_url, wait_until="domcontentloaded")
                    if not resp or resp.status != 200:
                        log_warning(
                            f"Playwright page.goto to {target_url} returned status code {getattr(resp, 'status', 'unknown')}"
                        )
                        return None
                    try:
                        raw_json = resp.json()
                    except Exception:
                        # Fallback: try to parse text as JSON if server mislabels content type
                        try:
                            import json as _json

                            raw_json = _json.loads(resp.text())
                        except Exception as json_fallback_err:
                            log_error(
                                f"Failed to parse response as JSON for {identifier}",
                                exception=json_fallback_err,
                            )
                            return None
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
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
    except Exception as e:
        log_error(f"Playwright check failed for {identifier}", exception=e)
        return None
