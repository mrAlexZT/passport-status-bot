from beanie import Document, Indexed


class PushModel(Document):
    telegram_id: str
    secret_id: str

    class Settings:
        name = "pushes"
