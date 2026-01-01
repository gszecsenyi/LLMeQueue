import time
import requests
from config import SERVER_URL, AUTH_TOKEN, POLL_INTERVAL
from embedder import get_embedding


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


def complete_task(task_id: str, embedding: list[float]):
    """Submit completed embedding to the server."""
    response = requests.post(
        f"{SERVER_URL}/worker/complete/{task_id}",
        headers=get_headers(),
        json={"embedding": embedding},
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


def process_task(task: dict):
    """Process a single task."""
    task_id = task["id"]
    text = task["text"]
    print(f"Processing task {task_id}: {text[:50]}...")

    try:
        embedding = get_embedding(text)
        complete_task(task_id, embedding)
        print(f"Completed task {task_id} (embedding dim: {len(embedding)})")
    except Exception as e:
        error_msg = str(e)
        print(f"Failed task {task_id}: {error_msg}")
        try:
            fail_task(task_id, error_msg)
        except Exception as fail_error:
            print(f"Could not report failure: {fail_error}")


def main():
    """Main worker loop."""
    print(f"Worker starting. Server: {SERVER_URL}")
    print(f"Poll interval: {POLL_INTERVAL}s")

    while True:
        try:
            task = claim_next_task()
            if task:
                process_task(task)
            else:
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nWorker stopped.")
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
