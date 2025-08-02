import asyncio
import aiohttp
from aiogram import Bot

from bot.core.config import settings
from bot.core.logger import log_error

loop = asyncio.get_event_loop()
bot = Bot(settings.TOKEN, loop=loop)

# Default values in case GitHub API is unavailable
DEFAULT_VERSION = "N/A"
DEFAULT_LINK = "https://github.com/mrAlexZT/passport-status-bot/releases/latest"
codename = "Silence"

async def get_latest_release():
    """Fetch latest release info from GitHub API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/repos/mrAlexZT/passport-status-bot/releases/latest",
                headers={"Accept": "application/vnd.github+json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["tag_name"].lstrip("v"), data["html_url"]
                else:
                    log_error(
                        "Failed to fetch release info",
                        None,
                        f"Status: {response.status}"
                    )
    except Exception as e:
        log_error("Failed to fetch release info", None, e)
    
    return DEFAULT_VERSION, DEFAULT_LINK

# Initialize version and link
version, link = DEFAULT_VERSION, DEFAULT_LINK

# Update version and link asynchronously
async def update_version():
    """Update version and link from GitHub."""
    global version, link
    v, l = await get_latest_release()
    version, link = v, l

# Schedule initial version update
loop.create_task(update_version())
