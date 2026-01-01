import os

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default-secret-token")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))  # seconds
