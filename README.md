# Embedding Queue

A simple distributed system for offloading text embedding tasks to a local GPU.

## What is this?

If you have a machine with a GPU but want to run your main application somewhere else (like AWS), this project lets you:

1. **Submit texts** from anywhere via a simple REST API
2. **Process embeddings** on your local GPU using Ollama
3. **Retrieve results** when they're ready

The queue server runs in the cloud, your GPU worker runs locally, and they communicate over HTTP.

## Architecture

```
Your App (cloud)          Queue Server (cloud)           Your PC (local GPU)
      │                          │                              │
      ├── Submit text ──────────►│                              │
      │                          │◄──── Worker polls for tasks ─┤
      │                          │                              │
      │                          │──── Send text to process ───►│
      │                          │                              ├── Ollama generates
      │                          │◄──── Return embedding ───────┤    embedding
      │                          │                              │
      ◄── Get result ────────────┤                              │
```

## Quick Start

### 1. Start the services

```bash
docker-compose up --build
```

### 2. Download an embedding model (first time only)

```bash
docker exec -it llmequeue-ollama-1 ollama pull nomic-embed-text
```

### 3. Get embeddings (OpenAI-compatible)

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
```

**Response (OpenAI format):**
```json
{
  "object": "list",
  "data": [{"object": "embedding", "embedding": [0.123, -0.456, ...], "index": 0}],
  "model": "nomic-embed-text"
}
```

The server waits for the result (default 10 seconds, max 30 seconds). If processing takes longer, it returns a task ID:

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
| `POST` | `/v1/embeddings` | **OpenAI-compatible** - sync with long polling |
| `GET` | `/tasks/{id}` | Get task status and result (for polling) |
| `GET` | `/tasks/{id}/result` | Get only the embedding |
| `GET` | `/health` | Health check |

All endpoints require `Authorization: Bearer your-secret-token` header.

### OpenAI Endpoint Details

`POST /v1/embeddings`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input` | string | required | Text to embed |
| `model` | string | `nomic-embed-text` | Model name (optional) |
| `wait_seconds` | int | `10` | Wait time in seconds (0 = return ID immediately, max 30) |

## Configuration

Edit `.env` file to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_TOKEN` | `your-secret-token` | API authentication token |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model to use |
| `POLL_INTERVAL` | `2` | Worker poll frequency (seconds) |
| `SERVER_PORT` | `8000` | Server port |
| `DB_PATH` | `data/embedding_queue.db` | SQLite database path |

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
│   ├── embedder.py      # Ollama client
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

## AWS Lightsail Deployment

Deploy the server container to AWS Lightsail for cloud hosting.

### 1. Install AWS CLI

```bash
pip install awscli
aws configure
```

### 2. Create a Lightsail container service

```bash
aws lightsail create-container-service \
  --service-name llmequeue \
  --power small \
  --scale 1
```

### 3. Build and push the server image

```bash
# Build the server image
docker build -t llmequeue-server ./server

# Push to Lightsail
aws lightsail push-container-image \
  --service-name llmequeue \
  --label server \
  --image llmequeue-server
```

### 4. Deploy the container

Update `lightsail-deploy.json` with the image name from step 3, then:

```bash
aws lightsail create-container-service-deployment \
  --service-name llmequeue \
  --cli-input-json file://lightsail-deploy.json
```

### 5. Get the public URL

```bash
aws lightsail get-container-services --service-name llmequeue
```

The URL will be in the format: `https://llmequeue.xxxxx.us-east-1.cs.amazonlightsail.com`

### 6. Run the worker locally

Point your local worker to the Lightsail server:

```bash
SERVER_URL=https://llmequeue.xxxxx.us-east-1.cs.amazonlightsail.com \
AUTH_TOKEN=your-secret-token \
docker-compose up worker ollama
```

### Lightsail Configuration

Edit `lightsail-deploy.json` to customize:

| Field | Description |
|-------|-------------|
| `serviceName` | Lightsail service name |
| `environment.AUTH_TOKEN` | API authentication token |
| `publicEndpoint.healthCheck` | Health check settings |
