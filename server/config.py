import os

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default-secret-token")
DB_PATH = os.getenv("DB_PATH", "data/embedding_queue.db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
