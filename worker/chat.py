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
    
    try:
        content = data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed Ollama API response: expected 'message.content' field, got: {data!r}") from exc
    
    return {
        "content": content,
        "finish_reason": "length" if not data.get("done") else "stop"
    }
