from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.core.models.application import StatusModel
from bot.core.utils import has_final_application_status, process_status_update


def test_has_final_application_status() -> None:
    statuses = [
        StatusModel(status="Заявка в обробці", date=1),
        StatusModel(status="Документ видано", date=2),
    ]

    assert has_final_application_status(statuses) is True


@pytest.mark.asyncio
async def test_process_status_update_skips_final_status() -> None:
    application = MagicMock()
    application.session_id = "1234567"
    application.statuses = [StatusModel(status="Документ видано", date=2)]
    application.save = AsyncMock()

    scraper = MagicMock()
    scraper.check = AsyncMock()
    notify_subscribers = AsyncMock()

    await process_status_update(application, scraper, notify_subscribers)

    scraper.check.assert_not_awaited()
    application.save.assert_not_awaited()
    notify_subscribers.assert_not_awaited()
