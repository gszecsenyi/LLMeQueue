import os

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default-secret-token")
DB_PATH = os.getenv("DB_PATH", "data/llmequeue.db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
