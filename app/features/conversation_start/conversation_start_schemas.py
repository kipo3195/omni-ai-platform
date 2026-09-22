# API Request / Response 모델 (외부와의 계약)

from datetime import datetime
from enum import Enum


from pydantic import BaseModel, Field

class SuggestionType(str, Enum):
    RECENT_CONTEXT = "RECENT_CONTEXT"
    TRENDING = "TRENDING"

class ChatMessage(BaseModel):
    sender_id: str
    sender_name: str | None = None
    content: str
    sent_at: datetime


class RequestOptions(BaseModel):
    max_suggestions: int = Field(default=3, ge=1)
    max_length: int = Field(default=80, ge=1)
    language: str = Field(default="ko")


class ConversationStartRequest(BaseModel):
    session_id: str
    user_id: str
    room_id: str
    suggestion_type: SuggestionType

    messages: list[ChatMessage] = Field(default_factory=list)
    options: RequestOptions = Field(default_factory=RequestOptions)


class ConversationStartSuggestion(BaseModel):
    topic: str
    question: str


class ConversationStartResponse(BaseModel):
    session_id: str
    suggestions: list[ConversationStartSuggestion]



    
