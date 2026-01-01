import requests
from config import OLLAMA_URL, CHAT_MODEL


def get_chat_completion(messages: list[dict], model: str = None, temperature: float = 0.7, max_tokens: int = None) -> dict:
    """Get chat completion from Ollama API."""
    payload = {
        "model": model or CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        }
    }
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=300,  # 5 minutes for longer generations
    )
    response.raise_for_status()
    data = response.json()
    return {
        "content": data["message"]["content"],
        "finish_reason": "stop" if data.get("done") else "length"
    }
