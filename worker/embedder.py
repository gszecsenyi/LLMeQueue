import requests
from config import OLLAMA_URL, EMBEDDING_MODEL


def get_embedding(text: str, model: str = None, dimensions: int = None) -> list[float]:
    """Get embedding from Ollama API."""
    payload = {
        "model": model or EMBEDDING_MODEL,
        "prompt": text,
    }
    if dimensions is not None:
        payload["dimensions"] = dimensions
    
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["embedding"]
