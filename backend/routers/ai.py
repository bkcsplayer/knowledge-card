"""
AI API Router
Endpoints for knowledge distillation and AI features
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.ai_service import ai_service
from config import settings

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


class DistillRequest(BaseModel):
    """Request model for knowledge distillation"""
    content: str
    context: Optional[str] = None


class QuestionRequest(BaseModel):
    """Request model for Q&A"""
    question: str
    context: Optional[str] = None


class DigestRequest(BaseModel):
    """Request model for daily digest"""
    knowledge_items: List[Dict[str, Any]]


@router.get("/status")
async def get_ai_status():
    """Check AI service configuration status"""
    return {
        "configured": settings.ai_configured,
        "model": settings.openrouter_model,
        "base_url": settings.openrouter_base_url
    }


@router.get("/test")
async def test_ai_connection():
    """Test AI API connection"""
    result = await ai_service.test_connection()
    
    if result["status"] == "error" and not result.get("configured"):
        raise HTTPException(status_code=503, detail=result["message"])
    
    return result


@router.post("/distill")
async def distill_knowledge(request: DistillRequest):
    """
    Distill knowledge from content
    
    Extracts key insights, summary, tags, and action items from raw content.
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    if not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    result = await ai_service.distill_knowledge(
        content=request.content,
        context=request.context
    )
    
    return result


@router.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Ask a question to the AI
    
    Optionally provide context from knowledge base for more accurate answers.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    answer = await ai_service.answer_question(
        question=request.question,
        context=request.context
    )
    
    return {
        "question": request.question,
        "answer": answer,
        "has_context": bool(request.context)
    }


@router.post("/digest")
async def generate_digest(request: DigestRequest):
    """
    Generate a daily digest from knowledge items
    
    Creates a summarized overview of multiple knowledge entries.
    """
    if not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    result = await ai_service.generate_daily_digest(request.knowledge_items)
    
    return result



