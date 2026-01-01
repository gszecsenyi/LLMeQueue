from pydantic import BaseModel
from typing import Optional, List


# Embedding models

class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int = 0


class OpenAIEmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str


class OpenAIEmbeddingRequest(BaseModel):
    input: str  # text to embed
    model: Optional[str] = None  # optional, uses server default


# Chat completion models

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: ChatUsage = ChatUsage()


class TaskResponse(BaseModel):
    id: str
    text: str
    status: str
    embedding: Optional[list[float]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class TaskResult(BaseModel):
    id: str
    embedding: list[float]


class WorkerCompleteRequest(BaseModel):
    embedding: list[float]


class WorkerFailRequest(BaseModel):
    error: str
