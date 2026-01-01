import json
import time
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Union

import database
from config import AUTH_TOKEN, EMBEDDING_MODEL
from models import (
    TaskResponse,
    TaskResult,
    WorkerCompleteRequest,
    WorkerFailRequest,
    EmbeddingData,
    OpenAIEmbeddingResponse,
    OpenAIEmbeddingRequest,
)

app = FastAPI(title="Embedding Queue API")


@app.on_event("startup")
def startup():
    database.init_db()


def verify_token(authorization: str = Header(...)) -> str:
    """Verify the Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


# Client endpoints

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, token: str = Depends(verify_token)):
    """Get task status and result."""
    task = database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    embedding = None
    if task["embedding"]:
        embedding = json.loads(task["embedding"])

    return TaskResponse(
        id=task["id"],
        text=task["text"],
        status=task["status"],
        embedding=embedding,
        error=task["error"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


@app.get("/tasks/{task_id}/result", response_model=TaskResult)
def get_task_result(task_id: str, token: str = Depends(verify_token)):
    """Get only the embedding result."""
    task = database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed (status: {task['status']})")
    if not task["embedding"]:
        raise HTTPException(status_code=500, detail="Task completed but no embedding found")

    return TaskResult(id=task["id"], embedding=json.loads(task["embedding"]))


# Worker endpoints

@app.post("/worker/next")
def worker_claim_next(token: str = Depends(verify_token)):
    """Claim the next pending task for processing."""
    task = database.claim_next_task()
    if not task:
        return {"task": None}
    return {"task": {"id": task["id"], "text": task["text"]}}


@app.post("/worker/complete/{task_id}")
def worker_complete(
    task_id: str,
    request: WorkerCompleteRequest,
    token: str = Depends(verify_token),
):
    """Submit embedding result for a task."""
    success = database.complete_task(task_id, request.embedding)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or not in processing state")
    return {"status": "completed"}


@app.post("/worker/fail/{task_id}")
def worker_fail(
    task_id: str,
    request: WorkerFailRequest,
    token: str = Depends(verify_token),
):
    """Report task failure."""
    success = database.fail_task(task_id, request.error)
    if not success:
        raise HTTPException(status_code=400, detail="Task not found or not in processing state")
    return {"status": "failed"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# OpenAI-compatible endpoint

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
    task_id = database.create_task(request.input)
    wait_seconds = request.wait_seconds if request.wait_seconds is not None else 10

    if wait_seconds > 0:
        max_wait = min(wait_seconds, 30)
        deadline = time.time() + max_wait

        while time.time() < deadline:
            result = database.get_task(task_id)

            if result["status"] == "completed":
                embedding = json.loads(result["embedding"])
                database.delete_task(task_id)
                return OpenAIEmbeddingResponse(
                    data=[EmbeddingData(embedding=embedding)],
                    model=request.model or EMBEDDING_MODEL
                )
            elif result["status"] == "failed":
                error_msg = result["error"] or "Unknown error"
                database.delete_task(task_id)
                raise HTTPException(status_code=500, detail=error_msg)

            await asyncio.sleep(0.2)

    # Timeout or no wait - return task ID for polling
    return {"id": task_id}
