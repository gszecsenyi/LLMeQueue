# LLMeQueue

A simple distributed system for offloading LLM tasks (embeddings and chat completions) to a local GPU.

## What is this?

If you have a machine with a GPU but want to run your main application somewhere else (like AWS), this project lets you:

1. **Submit requests** from anywhere via OpenAI-compatible REST API
2. **Process with Ollama** on your local GPU (embeddings or chat completions)
3. **Retrieve results** when they're ready

The queue server runs in the cloud, your GPU worker runs locally, and they communicate over HTTP.

## Architecture

```
Your App (cloud)          Queue Server (cloud)           Your PC (local GPU)
      │                          │                              │
      ├── Submit request ───────►│                              │
      │                          │◄──── Worker polls for tasks ─┤
      │                          │                              │
      │                          │──── Send task to process ───►│
      │                          │                              ├── Ollama processes
      │                          │◄──── Return result ──────────┤    (embed or chat)
      │                          │                              │
      ◄── Get result ────────────┤                              │
```

## Quick Start

### Option A: NVIDIA GPU (Linux/Windows with NVIDIA GPU)

```bash
# Start all services (3 workers for parallel processing)
docker compose -f docker-compose.nvidia.yml up --scale worker=3 --build

# Pull models (first time only)
docker exec -it llmequeue-ollama-1 ollama pull nomic-embed-text
docker exec -it llmequeue-ollama-1 ollama pull llama3.2
```

### Option B: Mac (Apple Silicon GPU)

```bash
# Install and run Ollama natively for GPU acceleration
brew install ollama
ollama serve  # In a separate terminal

# Pull models
ollama pull nomic-embed-text
ollama pull llama3.2

# Start server and 3 workers (parallel processing)
docker compose -f docker-compose.mac.yml up --scale worker=3 --build
```

### 3. Use the API (OpenAI-compatible)

#### Embeddings

**curl:**
```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"input": "The quick brown fox jumps over the lazy dog", "model": "nomic-embed-text"}'
```

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-secret-token",
    base_url="http://localhost:8000/v1"
)

response = client.embeddings.create(
    input="The quick brown fox jumps over the lazy dog",
    model="nomic-embed-text"
)

embedding = response.data[0].embedding

# Optional: Specify embedding dimensions (if model supports it)
response = client.embeddings.create(
    input="The quick brown fox jumps over the lazy dog",
    model="nomic-embed-text",
    dimensions=768
)
```

**Response (OpenAI format):**
```json
{
  "object": "list",
  "data": [{"object": "embedding", "embedding": [0.123, -0.456, ...], "index": 0}],
  "model": "nomic-embed-text"
}
```

The server waits up to 30 seconds for the result. If processing takes longer, it returns a task ID for polling.

#### Chat Completions

**curl:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}], "model": "llama3.2"}'
```

**Python (OpenAI SDK):**
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-secret-token",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    messages=[{"role": "user", "content": "Hello!"}],
    model="llama3.2"
)

print(response.choices[0].message.content)
```

**Response (OpenAI format):**
```json
{
  "id": "...",
  "object": "chat.completion",
  "choices": [{"message": {"role": "assistant", "content": "Hello! How can I help?"}, "finish_reason": "stop"}],
  "model": "llama3.2"
}
```

The server waits up to 180 seconds (3 minutes) for the result. If processing takes longer, it returns a task ID:

```json
{"id": "550e8400-e29b-41d4-a716-446655440000"}
```

Then poll for the result:

```bash
curl http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer your-secret-token"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/embeddings` | OpenAI-compatible embeddings |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat completions |
| `GET` | `/tasks/{id}` | Get task status and result (for polling) |
| `GET` | `/tasks/{id}/result` | Get only the result |
| `GET` | `/health` | Health check |

All endpoints require `Authorization: Bearer your-secret-token` header.

### OpenAI Endpoint Details

`POST /v1/embeddings`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input` | string | required | Text to embed |
| `model` | string | `nomic-embed-text` | Model name (optional) |
| `dimensions` | integer | null | Embedding dimension size (optional, must be positive) |

`POST /v1/chat/completions`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `messages` | array | required | Array of message objects with `role` and `content` |
| `model` | string | `llama3.2` | Model name (optional) |
| `temperature` | float | `0.7` | Sampling temperature |
| `max_tokens` | int | null | Maximum tokens to generate |

## Configuration

Edit `.env` file to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_TOKEN` | `your-secret-token` | API authentication token |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `CHAT_MODEL` | `llama3.2` | Ollama chat model |
| `POLL_INTERVAL` | `2` | Worker poll frequency (seconds) |
| `SERVER_PORT` | `8000` | Server port |
| `DB_PATH` | `data/llmequeue.db` | SQLite database path |

## Requirements

- Docker & Docker Compose
- NVIDIA GPU with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

## Project Structure

```
LLMeQueue/
├── server/              # FastAPI queue server
│   ├── main.py          # API endpoints
│   ├── database.py      # SQLite operations
│   ├── models.py        # Request/response models
│   └── config.py        # Configuration
├── worker/              # GPU worker client
│   ├── worker.py        # Polling loop
│   ├── embedder.py      # Ollama embeddings client
│   ├── chat.py          # Ollama chat client
│   └── config.py        # Configuration
├── docker-compose.yml
├── lightsail-deploy.json  # AWS Lightsail deployment
├── .env                 # Environment variables
└── data/                # SQLite database (persistent)
```

## Task States

- `pending` - Waiting to be processed
- `processing` - Worker is generating embedding
- `completed` - Embedding ready
- `failed` - Error occurred (check `error` field)

## Deployment

### Server (AWS)

**Note:** The server no longer has default models. Clients must specify the `model` field in requests.

```bash
# On AWS instance
git clone https://github.com/yourusername/LLMeQueue.git
cd LLMeQueue
cp .env.example .env
# Edit .env with your AUTH_TOKEN
docker compose up -d --build
```

### Worker (Local GPU)

Workers should specify default models via environment variables:

```bash
# Create .env file with your models
echo "EMBEDDING_MODEL=nomic-embed-text" >> .env
echo "CHAT_MODEL=llama3.2" >> .env
echo "SERVER_URL=http://your-aws-ip:8000" >> .env
echo "AUTH_TOKEN=your-secret-token" >> .env

# Deploy worker
docker compose -f docker-compose.cloud.yml up -d --build
```
