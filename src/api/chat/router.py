from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from settings.db import get_db

from .controllers import (get_conversation_history, get_last_conversations,
                          process_chat_request)
from .schema import (ChatRequest, GetConversationRequest,
                     GetConversationResponse, LastConversationsRequest,
                     LastConversationsResponse)

router = APIRouter()

################################################
################################################
### Chat Endpoint ###
################################################
################################################


@router.post("/chat")
async def chat(chat_request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat API endpoint that processes user messages and returns streamed AI responses.
    Requires signature verification and handles conversation management.
    """
    try:
        return await process_chat_request(chat_request, db)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing chat request: {str(e)}"
        )


################################################
################################################
### Last Conversations Endpoint ###
################################################
################################################


@router.post("/last-conversations", response_model=LastConversationsResponse)
async def get_recent_conversations(
    request: LastConversationsRequest, db: Session = Depends(get_db)
):
    """
    Retrieve the 5 most recent conversations for a user.
    Returns conversation keys and a preview of the last message.
    Requires signature verification for authentication.
    """
    try:
        return await get_last_conversations(request, db)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving conversations: {str(e)}"
        )


################################################
################################################
### Get Conversation History Endpoint ###
################################################
################################################


@router.post("/conversation", response_model=GetConversationResponse)
async def get_conversation(
    request: GetConversationRequest, db: Session = Depends(get_db)
):
    """
    Retrieve the full history of a specific conversation.
    Returns all messages and responses in chronological order.
    Requires signature verification and validates that the conversation
    belongs to the requesting user.
    """
    try:
        return await get_conversation_history(request, db)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving conversation: {str(e)}"
        )
