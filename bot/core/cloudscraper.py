import cloudscraper

from bot.core.logger import log_function, log_info, log_error

@log_function("cloudscraper_init")
async def cloudscraper_init(proxy_urls: list[str], debug: bool = False):
    # Create a scraper with all enhanced features
    scraper = cloudscraper.create_scraper(
        # Use js2py interpreter for better compatibility
        interpreter='js2py',

        # Enable proxy rotation
        rotating_proxies= proxy_urls,
        proxy_options={
            'rotation_strategy': 'smart',
            'ban_time': 300
        },

        # Enable stealth mode
        enable_stealth=True,
        stealth_options={
            'min_delay': 2.0,
            'max_delay': 6.0,
            'human_like_delays': True,
            'randomize_headers': True,
            'browser_quirks': True
        },

        # Set browser fingerprint
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },

        # Enable debugging if needed
        debug=debug
    )

    return scraper


@log_function("cloudscraper_get")
async def cloudscraper_get(scraper: cloudscraper.CloudScraper, test_url: str):
    try:
        response = scraper.get(test_url)
        log_info(f"Cloudscraper {test_url} response: {response.status_code}")

        return response
    except Exception as e:
        log_error(f"Error in cloudscraper_get: {e}")
        return None