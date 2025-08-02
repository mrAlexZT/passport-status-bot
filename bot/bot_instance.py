import asyncio
import aiohttp
from aiogram import Bot

from bot.core.config import settings
from bot.core.logger import log_error, log_function

loop = asyncio.get_event_loop()
bot = Bot(settings.TOKEN, loop=loop)

# Default values in case GitHub API is unavailable
DEFAULT_VERSION = "N/A"
DEFAULT_LINK = "https://github.com/mrAlexZT/passport-status-bot/releases/latest"
codename = "Silence"

@log_function("get_latest_release")
async def get_latest_release():
    """
    Fetch latest release info from GitHub API.
    Returns tuple of (version, link, is_prerelease).
    """
    try:
        async with aiohttp.ClientSession() as session:
            # First try to get all releases to find latest stable
            async with session.get(
                "https://api.github.com/repos/mrAlexZT/passport-status-bot/releases",
                headers={"Accept": "application/vnd.github+json"}
            ) as response:
                if response.status == 200:
                    releases = await response.json()
                    
                    # Filter out drafts and find latest stable release
                    stable_releases = [
                        r for r in releases 
                        if not r["draft"] and not r["prerelease"]
                    ]
                    
                    if stable_releases:
                        latest = stable_releases[0]  # Releases are sorted by date
                        version = latest["tag_name"].lstrip("v")
                        link = latest["html_url"]
                        return version, link
                    
                    # If no stable releases found, try to get any release
                    if releases:
                        latest = releases[0]
                        version = latest["tag_name"].lstrip("v")
                        link = latest["html_url"]
                        return version, link
                    
                    log_error(
                        "No releases found",
                        None,
                        "Repository has no releases"
                    )
                else:
                    log_error(
                        "Failed to fetch releases",
                        None,
                        f"Status: {response.status}, Response: {await response.text()}"
                    )
    except Exception as e:
        log_error("Failed to fetch release info", None, str(e))
    
    return DEFAULT_VERSION, DEFAULT_LINK

# Initialize version and link
version, link = DEFAULT_VERSION, DEFAULT_LINK

# Update version and link asynchronously
@log_function("update_version")
async def update_version():
    """Update version and link from GitHub."""
    global version, link
    v, l = await get_latest_release()
    if v != "N/A":  # Only update if we got a valid version
        version, link = v, l

@log_function("version_check_loop")
async def version_check_loop():
    """Periodically check for new versions."""
    while True:
        await update_version()
        await asyncio.sleep(3600)  # Check every hour

# Schedule version updates
loop.create_task(update_version())  # Initial update
loop.create_task(version_check_loop())  # Periodic updates
