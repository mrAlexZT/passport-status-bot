import asyncio
import functools
import json
import secrets

import cloudscraper
import requests

from bot.core.logger import log_error, log_function, log_info, log_warning
from bot.core.playwright import playwright_check


class AsyncCloudScraper:
    """
    An asynchronous client for making web requests that can bypass Cloudflare.
    Uses asyncio.run_in_executor to offload blocking cloudscraper calls.
    """

    def __init__(self) -> None:
        self.scraper = cloudscraper.create_scraper()
        log_info("Cloudscraper instance created.")

    @log_function("fetch_sync")
    def _fetch_sync(self, url: str) -> requests.Response:
        """
        Synchronous method to perform the blocking cloudscraper request.
        This method will be run in a separate thread.
        """
        log_info(f"Starting synchronous request for {url} on a background thread.")
        response: requests.Response = self.scraper.get(url)
        log_info(
            f"Synchronous request for {url} completed with status code {response.status_code}."
        )
        return response

    @log_function("check")
    async def check(
        self,
        identifier: str,
        retrieve_all: bool = False,
        fallback_to_playwright: bool = True,
    ) -> list[dict[str, str]] | None:
        """
        Asynchronous method to schedule the blocking request and await its result.
        """
        test_url = f"https://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&_={secrets.randbelow(10**13) + 10**12}"
        log_info(f"Target URL: {test_url}")

        try:
            loop = asyncio.get_running_loop()
            log_info(f"Current event loop: {loop}")

            blocking_func = functools.partial(self._fetch_sync, test_url)

            log_info("Scheduling synchronous request to run in an executor.")
            response = await loop.run_in_executor(None, blocking_func)

            if not response:
                raise ValueError("Empty response from Cloudscraper.")

            raw_json = json.loads(response.text)
            log_info(f"Raw JSON received: {raw_json}")

            parsed_json = raw_json.get("StatusInfo", [])
            if not parsed_json:
                raise ValueError("Empty 'StatusInfo' in response.")

            status_list = [
                {"status": item["StatusName"], "date": item["StatusDateUF"]}
                for item in parsed_json
            ]

        except Exception as e:
            log_error(f"Error during AsyncCloudScraper request: {e}")
            if fallback_to_playwright:
                try:
                    log_info("Falling back to Playwright method.")
                    result = await playwright_check(
                        identifier, retrieve_all=retrieve_all
                    )
                    log_info("Playwright path succeeded.")
                    # Ensure result is of the correct type for mypy
                    if result is None or (
                        isinstance(result, list)
                        and all(
                            isinstance(item, dict)
                            and all(
                                isinstance(k, str) and isinstance(v, str)
                                for k, v in item.items()
                            )
                            for item in result
                        )
                    ):
                        return result
                    else:
                        log_error("Playwright path returned unexpected type.")
                        return None
                except Exception as e2:
                    log_error(f"Playwright path failed: {e2}")

            log_warning("Both Cloudscraper and Playwright paths failed.")
            return None

        if not status_list:
            return None
        return status_list if retrieve_all else [status_list[-1]]
