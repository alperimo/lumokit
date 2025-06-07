from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

#################################################
#### CHAT ENDPOINT SCHEMA ####
#################################################

# Define allowed models
AllowedModelName = Literal[
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "anthropic/claude-3.7-sonnet",
    "google/gemini-2.5-pro-preview",
    "meta-llama/llama-4-maverick",
    "lumo-70b",
    "lumo-8b",
    "lumo-deepseek-8b",
]


class ChatRequest(BaseModel):
    public_key: str
    signature: str
    agent_public: Optional[str] = None
    agent_private: Optional[str] = None
    conversation_key: Optional[str] = None
    message: str
    model_name: Optional[AllowedModelName] = Field(default="gpt-4.1-mini")
    temperature: Optional[float] = Field(default=0.7)
    tools: Optional[List[str]] = Field(default=[])

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class ChatResponse(BaseModel):
    success: bool
    conversation_key: str
    message: Optional[str] = None
    error: Optional[str] = None

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class LastConversationsRequest(BaseModel):
    public_key: str
    signature: str

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class ConversationSummary(BaseModel):
    conversation_key: str
    last_message_preview: str
    timestamp: datetime

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class LastConversationsResponse(BaseModel):
    success: bool
    conversations: List[ConversationSummary] = []
    error: Optional[str] = None

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class GetConversationRequest(BaseModel):
    public_key: str
    signature: str
    conversation_key: str

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class MessageResponse(BaseModel):
    id: int
    message: str
    response: Optional[str] = None
    timestamp: datetime

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())


class GetConversationResponse(BaseModel):
    success: bool
    conversation_key: str
    messages: List[MessageResponse] = []
    error: Optional[str] = None

    # Disable protected namespace warnings
    model_config = ConfigDict(protected_namespaces=())
