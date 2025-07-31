from beanie import Document
from datetime import datetime

class RequestLog(Document):
    telegram_id: str
    timestamp: datetime

    class Settings:
        name = "request_logs"

