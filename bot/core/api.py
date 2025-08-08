# Standard library imports
import os
from datetime import datetime
import random

# Third party imports
import cloudscraper
from fake_headers import Headers

# Local application imports
from bot.core.logger import log_error, log_warning, log_function
from bot.core.playwright import playwright_check


class Scraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    @log_function("check")
    def check(self, identifier, retrive_all=False, fallback_to_playwright=True):

        try:
            target_url = f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}&_={random.randint(1000000000000, 1999999999999)}"
            headers = Headers().generate()

            r = self.scraper.get(
                target_url,
                headers=headers,
            )

            # If the request is not successful, log the warning and return None
            if r.status_code != 200:
                log_warning(f"Request to {target_url} with headers {headers} returned status code {r.status_code}")
                log_warning(f"Response content: {r.content}")

            # If the request is successful, parse the response content
            if r.content:
                raw_json = r.json()
                parsed_json = raw_json["StatusInfo"]

                status_list = []
                for status in parsed_json:
                    status_list.append(
                        {
                            "status": status["StatusName"],
                            "date": status["StatusDateUF"],
                        }
                    )

                # If the user wants to retrieve all statuses, return the list
                if retrive_all:
                    return status_list

                return [status_list[-1]]
            # Fallback to Playwright in case content is empty/malformed
            if fallback_to_playwright:
                return playwright_check(identifier, retrive_all=retrive_all)
        except Exception as e:
            log_warning(f"Cloudscraper failed for {identifier}, trying Playwright. Error: {e}")
            try:
                if fallback_to_playwright:
                    return playwright_check(identifier, retrive_all=retrive_all)
            except Exception as e2:
                log_error(f"Error checking status for {identifier} via Playwright: {e2}")
                return None
