"""
Chatbot API routes for VoltCast AI assistant.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from ..services.chatbot import get_chatbot, VoltCastChatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chatbot"])


class ChatMessage(BaseModel):
    """Chat message model."""
    user: str = Field(..., description="User message")
    assistant: str = Field(..., description="Assistant response")
    timestamp: str = Field(..., description="Message timestamp")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message", min_length=1, max_length=500)
    conversation_history: Optional[List[ChatMessage]] = Field(None, description="Previous conversation context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Why is the electricity demand so high today?",
                "conversation_history": [
                    {
                        "user": "What's the current demand?",
                        "assistant": "The current electricity demand is 5,240 MW...",
                        "timestamp": "2023-01-07T15:00:00"
                    }
                ]
            }
        }


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Chatbot response")
    context: Dict[str, Any] = Field(..., description="Current system context")
    timestamp: str = Field(..., description="Response timestamp")
    model: str = Field(..., description="AI model used")
    success: bool = Field(..., description="Response success status")
    error: Optional[str] = Field(None, description="Error message if any")


class SuggestedQuestionsResponse(BaseModel):
    """Suggested questions response model."""
    questions: List[str] = Field(..., description="List of suggested questions")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    chatbot: VoltCastChatbot = Depends(get_chatbot)
):
    """
    Chat with VoltCast AI assistant about weather and electricity demand.
    
    The assistant can answer questions about:
    - Current electricity demand and trends
    - Weather impact on power consumption
    - Demand forecasting insights
    - Seasonal and daily patterns
    - System performance and accuracy
    """
    try:
        # Convert conversation history to dict format
        history = None
        if request.conversation_history:
            history = [
                {
                    "user": msg.user,
                    "assistant": msg.assistant,
                    "timestamp": msg.timestamp
                }
                for msg in request.conversation_history
            ]
        
        # Get chatbot response
        result = await chatbot.chat(request.message, history)
        
        return ChatResponse(**result)
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat service error: {str(e)}"
        )


@router.get("/chat/suggestions", response_model=SuggestedQuestionsResponse)
async def get_suggested_questions(
    chatbot: VoltCastChatbot = Depends(get_chatbot)
):
    """
    Get suggested questions for the chatbot.
    
    Returns a list of example questions users can ask about
    weather and electricity demand.
    """
    try:
        questions = chatbot.get_suggested_questions()
        return SuggestedQuestionsResponse(questions=questions)
    
    except Exception as e:
        logger.error(f"Suggestions endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Suggestions service error: {str(e)}"
        )


@router.get("/chat/status")
async def get_chatbot_status(
    chatbot: VoltCastChatbot = Depends(get_chatbot)
):
    """
    Get chatbot service status and current context.
    
    Returns information about the chatbot's availability and
    current system context for debugging.
    """
    try:
        context = chatbot._get_current_context()
        
        return {
            "status": "online",
            "model": "gemini-pro",
            "context": context,
            "features": [
                "Weather impact analysis",
                "Demand forecasting insights",
                "Real-time data integration",
                "Conversational AI"
            ]
        }
    
    except Exception as e:
        logger.error(f"Status endpoint error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "model": "gemini-pro"
        }