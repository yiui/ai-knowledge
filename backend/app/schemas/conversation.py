from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    knowledge_base_id: int | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    knowledge_base_id: int | None = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: int
    title: str
    knowledge_base_id: int | None
    message_count: int
    max_messages: int
    should_start_new: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: int
    title: str
    knowledge_base_id: int | None
    message_count: int
    max_messages: int
    should_start_new: bool
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatStreamRequest(BaseModel):
    question: str = Field(min_length=1)


class ChatLimitsResponse(BaseModel):
    max_messages_per_conversation: int
