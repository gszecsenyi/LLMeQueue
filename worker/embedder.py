import requests
from config import OLLAMA_URL, EMBEDDING_MODEL


def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama API."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "prompt": text,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["embedding"]
