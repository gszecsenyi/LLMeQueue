# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLMeQueue is a distributed LLM task queue system. A FastAPI server accepts requests (OpenAI-compatible API for embeddings and chat completions), stores them in SQLite, and a worker polls for tasks and processes them using Ollama on a local GPU.

## Commands

```bash
# NVIDIA GPU (Linux/Windows)
docker compose -f docker-compose.nvidia.yml up --build
docker exec -it llmequeue-ollama-1 ollama pull nomic-embed-text
docker exec -it llmequeue-ollama-1 ollama pull llama3.2

# Mac (Apple Silicon) - run Ollama natively for GPU
brew install ollama && ollama serve  # separate terminal
ollama pull nomic-embed-text && ollama pull llama3.2
docker compose -f docker-compose.mac.yml up --build

# Cloud deployment (server only)
docker build -t llmequeue-server ./server
```

## Architecture

```
Client -> Server (FastAPI) -> SQLite queue -> Worker polls -> Ollama (GPU)
```

**Server** (`server/`): FastAPI app exposing OpenAI-compatible `/v1/embeddings` and `/v1/chat/completions` endpoints. Uses long-polling to wait for results. Falls back to returning task ID for async polling.

**Worker** (`worker/`): Polls server for pending tasks, calls Ollama API for embeddings or chat completions, reports results back. Runs in a continuous loop with configurable poll interval.

**Task Flow**: `pending` -> `processing` (claimed by worker) -> `completed`/`failed`

## Key Files

- `server/main.py` - API endpoints and request handling
- `server/database.py` - SQLite operations with atomic task claiming (prevents race conditions)
- `worker/worker.py` - Polling loop and task processing
- `worker/embedder.py` - Ollama embeddings client
- `worker/chat.py` - Ollama chat completions client

## Environment Variables

Configure via `.env` or environment:
- `AUTH_TOKEN` - API authentication (required for all endpoints)
- `EMBEDDING_MODEL` - Ollama embedding model (default: `nomic-embed-text`)
- `CHAT_MODEL` - Ollama chat model (default: `llama3.2`)
- `POLL_INTERVAL` - Worker poll frequency in seconds (default: `2`)
- `SERVER_PORT` - Server port (default: `8000`)
- `DB_PATH` - SQLite database path (default: `data/llmequeue.db`)
