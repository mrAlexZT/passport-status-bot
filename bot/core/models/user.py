from beanie import Document, Indexed


class UserModel(Document):
    telegram_id: str
    session_id: str

    class Settings:
        name = "users"


class SubscriptionModel(Document):
    telegram_id: str
    session_id: str

    class Settings:
        name = "subscriptions"
