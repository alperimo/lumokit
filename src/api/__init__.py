from fastapi import APIRouter

from .chat.router import router as chat_api_router
from .users.router import router as users_api_router

router = APIRouter()

router.include_router(users_api_router, prefix="/user", tags=["User API Requests"])
router.include_router(chat_api_router, prefix="/chat", tags=["Chat API Requests"])
