import os

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "default-secret-token")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1"))  # poll interval in seconds (default 1s, float allows more granular control)
MAX_POLL_INTERVAL = float(os.getenv("MAX_POLL_INTERVAL", "10"))  # max backoff seconds
