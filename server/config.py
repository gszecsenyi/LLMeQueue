import os

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default-secret-token")
DB_PATH = os.getenv("DB_PATH", "data/llmequeue.db")

class Config:
    def __init__(self):
        self.auth_token = AUTH_TOKEN
        self.db_path = DB_PATH

config = Config()
