from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from bot.core.config import settings

client: AsyncMongoClient = AsyncMongoClient(
    settings.DATABASE_URL, uuidRepresentation="standard"
)
db: AsyncDatabase = client[settings.DATABASE_NAME]
