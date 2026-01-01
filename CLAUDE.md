# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLMeQueue is a distributed text embedding queue system. A FastAPI server accepts embedding requests (OpenAI-compatible API), stores them in SQLite, and a worker polls for tasks and processes them using Ollama on a local GPU.

## Commands

```bash
# Start all services (server, worker, ollama)
docker-compose up --build

# First-time setup: pull the embedding model
docker exec -it llmequeue-ollama-1 ollama pull nomic-embed-text

# Run only the server (for cloud deployment)
docker build -t llmequeue-server ./server

# Run worker locally against remote server
SERVER_URL=https://your-server.com AUTH_TOKEN=your-token docker-compose up worker ollama
```

## Architecture

```
Client -> Server (FastAPI) -> SQLite queue -> Worker polls -> Ollama (GPU)
```

**Server** (`server/`): FastAPI app exposing OpenAI-compatible `/v1/embeddings` endpoint. Uses long-polling (default 10s, max 30s) to wait for results. Falls back to returning task ID for async polling.

**Worker** (`worker/`): Polls server for pending tasks, calls Ollama API for embeddings, reports results back. Runs in a continuous loop with configurable poll interval.

**Task Flow**: `pending` -> `processing` (claimed by worker) -> `completed`/`failed`

## Key Files

- `server/main.py` - API endpoints and request handling
- `server/database.py` - SQLite operations with atomic task claiming (prevents race conditions)
- `worker/worker.py` - Polling loop and task processing
- `worker/embedder.py` - Ollama API client

## Environment Variables

Configure via `.env` or environment:
- `AUTH_TOKEN` - API authentication (required for all endpoints)
- `EMBEDDING_MODEL` - Ollama model name (default: `nomic-embed-text`)
- `POLL_INTERVAL` - Worker poll frequency in seconds (default: `2`)
- `SERVER_PORT` - Server port (default: `8000`)
- `DB_PATH` - SQLite database path (default: `data/embedding_queue.db`)
