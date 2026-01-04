from pydantic import BaseModel, Field
from typing import Optional, List, Any, Union


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
    model: str  # Remove default value
    dimensions: Optional[int] = Field(default=None, gt=0)  # Optional embedding dimension size


# Chat completion models

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: str  # Remove default value
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    wait_seconds: int = Field(default=180, ge=0, le=300)


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


class WorkerCompleteRequest(BaseModel):
    result: Any  # Generic result field for any task type (can be dict, list, etc.)


class WorkerFailRequest(BaseModel):
    error: str
