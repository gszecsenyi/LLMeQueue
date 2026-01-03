import json
import time
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header
from contextlib import asynccontextmanager
from typing import Union

import database
from config import AUTH_TOKEN, EMBEDDING_MODEL, CHAT_MODEL
from models import (
    WorkerFailRequest,
    EmbeddingData,
    OpenAIEmbeddingResponse,
    OpenAIEmbeddingRequest,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ChatChoice,
    WorkerCompleteRequest,
)


cleanup_task = None


async def periodic_cleanup():
    """Background task to periodically clean up old tasks."""
    while True:
        try:
            await asyncio.sleep(600)  # Run every 10 minutes
            await database.cleanup_old_tasks()
        except asyncio.CancelledError:
            # Task was cancelled (e.g., during application shutdown); exit cleanly.
            break
        except Exception as e:
            print(f"Cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    global cleanup_task
    await database.init_db()
    cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="LLMeQueue API", lifespan=lifespan)


def verify_token(authorization: str = Header(...)) -> str:
    """Verify the Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


# Client endpoints

@app.get("/tasks/{task_id}")
async def get_task(task_id: str, token: str = Depends(verify_token)):
    """Get task status and result."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = None
    if task["result"]:
        result = json.loads(task["result"])

    return {
        "id": task["id"],
        "task_type": task["task_type"],
        "status": task["status"],
        "result": result,
        "error": task["error"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
    }


@app.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, token: str = Depends(verify_token)):
    """Get only the result."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed (status: {task['status']})")
    if not task["result"]:
        raise HTTPException(status_code=500, detail="Task completed but no result found")

    return {"id": task["id"], "result": json.loads(task["result"])}


# Worker endpoints

@app.post("/worker/next")
async def worker_claim_next(token: str = Depends(verify_token)):
    """Claim the next pending task for processing."""
    task = await database.claim_next_task()
    if not task:
        return {"task": None}
    return {"task": {"id": task["id"], "task_type": task["task_type"], "payload": task["payload"]}}


@app.post("/worker/complete/{task_id}")
async def worker_complete(
    task_id: str,
    request: WorkerCompleteRequest,
    token: str = Depends(verify_token),
):
    """Submit result for a task."""
    result = request.result
    if result is None:
        raise HTTPException(status_code=400, detail="Missing 'result' field")
    success = await database.complete_task(task_id, result)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or not in processing state")
    return {"status": "completed"}


@app.post("/worker/fail/{task_id}")
async def worker_fail(
    task_id: str,
    request: WorkerFailRequest,
    token: str = Depends(verify_token),
):
    """Report task failure."""
    success = await database.fail_task(task_id, request.error)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or not in processing state")
    return {"status": "failed"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# OpenAI-compatible endpoints

@app.post("/v1/embeddings", response_model=Union[OpenAIEmbeddingResponse, dict])
async def openai_embeddings(request: OpenAIEmbeddingRequest, token: str = Depends(verify_token)):
    """OpenAI-compatible embeddings endpoint.

    Request:
        {"input": "text to embed", "model": "nomic-embed-text"}

    Response (OpenAI format):
        {"object": "list", "data": [{"embedding": [...]}], "model": "..."}

    On timeout:
        {"id": "task-id"} - poll GET /tasks/{id} for result
    """
    payload = {"text": request.input, "model": request.model or EMBEDDING_MODEL}
    task_id = await database.create_task("embedding", payload)
    max_wait = 30  # Fixed wait time for embeddings
    deadline = time.time() + max_wait

    while time.time() < deadline:
        task = await database.get_task(task_id)

        if task["status"] == "completed":
            embedding = json.loads(task["result"])
            await database.delete_task(task_id)
            return OpenAIEmbeddingResponse(
                data=[EmbeddingData(embedding=embedding)],
                model=request.model or EMBEDDING_MODEL
            )
        elif task["status"] == "failed":
            error_msg = task["error"] or "Unknown error"
            await database.delete_task(task_id)
            raise HTTPException(status_code=500, detail=error_msg)

        await asyncio.sleep(0.2)

    # Timeout - return task ID for polling
    return {"id": task_id}


@app.post("/v1/chat/completions", response_model=Union[ChatCompletionResponse, dict])
async def chat_completions(request: ChatCompletionRequest, token: str = Depends(verify_token)):
    """OpenAI-compatible chat completions endpoint.

    Request:
        {"messages": [{"role": "user", "content": "Hello"}], "model": "llama3.2"}

    Response (OpenAI format):
        {"id": "...", "choices": [{"message": {"role": "assistant", "content": "..."}}], ...}

    On timeout:
        {"id": "task-id"} - poll GET /tasks/{id} for result
    """
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming not supported")

    payload = {
        "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        "model": request.model or CHAT_MODEL,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    task_id = await database.create_task("chat", payload)
    max_wait = 180  # Fixed wait time for chat
    deadline = time.time() + max_wait

    while time.time() < deadline:
        task = await database.get_task(task_id)

        if task["status"] == "completed":
            result = json.loads(task["result"])
            await database.delete_task(task_id)
            return ChatCompletionResponse(
                id=task_id,
                created=int(time.time()),
                model=request.model or CHAT_MODEL,
                choices=[ChatChoice(
                    message=ChatMessage(role="assistant", content=result["content"]),
                    finish_reason=result.get("finish_reason", "stop")
                )]
            )
        elif task["status"] == "failed":
            error_msg = task["error"] or "Unknown error"
            await database.delete_task(task_id)
            raise HTTPException(status_code=500, detail=error_msg)

        await asyncio.sleep(0.2)

    # Timeout - return task ID for polling
    return {"id": task_id}
