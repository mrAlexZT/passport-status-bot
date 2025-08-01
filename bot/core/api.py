import os

from fake_headers import Headers
import cloudscraper
from datetime import datetime

from bot.core.logger import log_error, log_warning, log_function


class Scraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    @log_function("check")
    def check(self, identifier, retrive_all=False):
        try:
            headers = Headers().generate()

            r = self.scraper.get(
                f"http://passport.mfa.gov.ua/Home/CurrentSessionStatus?sessionId={identifier}",
                headers=headers,
            )

            # Log warning if response code not 200
            if r.status_code != 200:
                log_warning(f"Unexpected status code {r.status_code} for identifier {identifier} with headers {headers}")
                return None

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

                if retrive_all:
                    return status_list

                return [status_list[-1]]
            return None
        except Exception as e:
            log_error(f"Error checking status for {identifier}: {e}")
            return None
