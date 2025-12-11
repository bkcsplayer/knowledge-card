"""
Learning Path API Router
Generate learning roadmaps based on knowledge base
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.knowledge import Knowledge
from services.ai_service import ai_service
from config import settings

router = APIRouter(prefix="/api/v1/learning", tags=["Learning"])


class LearningPathRequest(BaseModel):
    """Request for generating learning path"""
    topic: str  # e.g., "React", "Python", "机器学习"
    level: str = "beginner"  # beginner, intermediate, advanced
    include_knowledge_ids: Optional[List[int]] = None  # Specific knowledge to include


class LearningStep(BaseModel):
    """A step in the learning path"""
    order: int
    title: str
    description: str
    duration: str  # e.g., "1-2 hours", "1 week"
    knowledge_ids: List[int]  # Related knowledge from our database
    resources: List[str]  # External resources or tips


class LearningPathResponse(BaseModel):
    """Generated learning path"""
    topic: str
    level: str
    total_duration: str
    steps: List[LearningStep]
    prerequisites: List[str]
    goals: List[str]


@router.post("/generate", response_model=LearningPathResponse)
async def generate_learning_path(
    request: LearningPathRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a learning path for a topic based on knowledge base
    
    AI will analyze related knowledge and create a structured learning roadmap
    """
    if not settings.ai_configured:
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    # Get related knowledge from database
    search_pattern = f"%{request.topic}%"
    result = await db.execute(
        select(Knowledge)
        .where(Knowledge.is_archived == False)
        .where(
            Knowledge.title.ilike(search_pattern) |
            Knowledge.category.ilike(search_pattern) |
            Knowledge.tags.contains([request.topic])
        )
        .limit(20)
    )
    related_knowledge = result.scalars().all()
    
    # Build context for AI
    knowledge_context = "\n".join([
        f"- 《{k.title}》(ID:{k.id}): {k.summary or k.original_content[:200]}"
        for k in related_knowledge
    ])
    
    # Generate learning path with AI
    prompt = f"""请为主题「{request.topic}」生成一个{request.level}级别的学习路线。

知识库中相关内容:
{knowledge_context if knowledge_context else "暂无相关知识"}

请按以下 JSON 格式返回学习路线:
{{
    "topic": "{request.topic}",
    "level": "{request.level}",
    "total_duration": "预计总学习时间",
    "prerequisites": ["先修知识1", "先修知识2"],
    "goals": ["学习目标1", "学习目标2", "学习目标3"],
    "steps": [
        {{
            "order": 1,
            "title": "步骤标题",
            "description": "详细描述这一步要学什么",
            "duration": "预计时间",
            "knowledge_ids": [相关知识ID列表],
            "resources": ["学习建议或资源"]
        }}
    ]
}}

要求:
1. 步骤由浅入深，循序渐进
2. 每个步骤包含明确的学习内容
3. 尽量关联知识库中的已有知识（使用ID）
4. 给出实用的学习建议"""

    import json
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学习规划师，擅长制定结构化的学习路线。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            data = response.json()
            result_text = data["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            cleaned = result_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            path_data = json.loads(cleaned.strip())
            
            return LearningPathResponse(**path_data)
            
    except Exception as e:
        # Fallback: generate basic path
        return LearningPathResponse(
            topic=request.topic,
            level=request.level,
            total_duration="待定",
            prerequisites=[],
            goals=[f"掌握 {request.topic} 基础知识"],
            steps=[
                LearningStep(
                    order=1,
                    title=f"{request.topic} 入门",
                    description=f"学习 {request.topic} 的基本概念和用法",
                    duration="1-2 周",
                    knowledge_ids=[k.id for k in related_knowledge[:3]],
                    resources=["查看知识库中的相关内容"]
                )
            ]
        )


@router.get("/topics")
async def get_available_topics(db: AsyncSession = Depends(get_db)):
    """
    Get list of topics that have enough knowledge for learning paths
    """
    # Get all categories and tags
    result = await db.execute(
        select(Knowledge.category, Knowledge.tags)
        .where(Knowledge.is_archived == False)
        .where(Knowledge.is_processed == True)
    )
    
    categories = set()
    tags = set()
    
    for row in result.fetchall():
        if row.category:
            categories.add(row.category)
        if row.tags:
            for tag in row.tags:
                tags.add(tag)
    
    return {
        "categories": list(categories),
        "popular_tags": list(tags)[:20],
        "suggested_topics": list(categories)[:5] + list(tags)[:5]
    }

