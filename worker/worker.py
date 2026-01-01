import time
import requests
from config import SERVER_URL, AUTH_TOKEN, POLL_INTERVAL, MAX_POLL_INTERVAL
from embedder import get_embedding
from chat import get_chat_completion


def get_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}


def claim_next_task():
    """Request the next task from the server."""
    response = requests.post(
        f"{SERVER_URL}/worker/next",
        headers=get_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("task")


def complete_task(task_id: str, result: any):
    """Submit completed result to the server."""
    response = requests.post(
        f"{SERVER_URL}/worker/complete/{task_id}",
        headers=get_headers(),
        json={"result": result},
        timeout=30,
    )
    response.raise_for_status()


def fail_task(task_id: str, error: str):
    """Report task failure to the server."""
    response = requests.post(
        f"{SERVER_URL}/worker/fail/{task_id}",
        headers=get_headers(),
        json={"error": error},
        timeout=30,
    )
    response.raise_for_status()


def process_embedding_task(task_id: str, payload: dict):
    """Process an embedding task."""
    text = payload["text"]
    model = payload.get("model")
    print(f"[embedding] {task_id}: {text[:50]}...")

    embedding = get_embedding(text, model)
    complete_task(task_id, embedding)
    print(f"[embedding] {task_id} completed (dim: {len(embedding)})")


def process_chat_task(task_id: str, payload: dict):
    """Process a chat completion task."""
    messages = payload["messages"]
    model = payload.get("model")
    temperature = payload.get("temperature", 0.7)
    max_tokens = payload.get("max_tokens")
    print(f"[chat] {task_id}: {len(messages)} messages, model={model}")

    result = get_chat_completion(messages, model, temperature, max_tokens)
    complete_task(task_id, result)
    print(f"[chat] {task_id} completed ({len(result['content'])} chars)")


def process_task(task: dict):
    """Process a single task."""
    task_id = task["id"]
    task_type = task["task_type"]
    payload = task["payload"]

    try:
        if task_type == "embedding":
            process_embedding_task(task_id, payload)
        elif task_type == "chat":
            process_chat_task(task_id, payload)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    except Exception as e:
        error_msg = str(e)
        print(f"[{task_type}] {task_id} failed: {error_msg}")
        try:
            fail_task(task_id, error_msg)
        except Exception as fail_error:
            print(f"Could not report failure: {fail_error}")


def main():
    """Main worker loop with exponential backoff."""
    print(f"Worker starting. Server: {SERVER_URL}")
    print(f"Poll interval: {POLL_INTERVAL}s, max backoff: {MAX_POLL_INTERVAL}s")

    backoff = POLL_INTERVAL
    
    while True:
        try:
            task = claim_next_task()
            if task:
                process_task(task)
                # Reset backoff on successful task claim
                backoff = POLL_INTERVAL
            else:
                # No task - exponential backoff
                time.sleep(backoff)
                backoff = min(backoff * 1.5, MAX_POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nWorker stopped.")
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 1.5, MAX_POLL_INTERVAL)


if __name__ == "__main__":
    main()
