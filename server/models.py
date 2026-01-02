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


class WorkerCompleteRequest(BaseModel):
    result: dict  # Generic result field for any task type


class WorkerFailRequest(BaseModel):
    error: str
