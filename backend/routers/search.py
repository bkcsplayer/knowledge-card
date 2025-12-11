"""
Search API Router
Semantic search using vector embeddings
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from database import get_db
from models.knowledge import Knowledge
from services.embedding_service import embedding_service
from services.ai_service import ai_service
from config import settings

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    limit: int = 10
    include_answer: bool = False  # Whether to generate AI answer


class SearchResult(BaseModel):
    """Search result model"""
    id: int
    title: str
    summary: Optional[str]
    category: Optional[str]
    tags: List[str]
    similarity: float
    snippet: str


class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    answer: Optional[str] = None
    total: int


@router.post("/", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Perform semantic search on knowledge base
    
    - **query**: Search query text
    - **limit**: Maximum number of results (1-50)
    - **include_answer**: Generate AI answer based on results
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    limit = min(max(request.limit, 1), 50)
    
    # Generate embedding for query
    query_embedding = await embedding_service.get_embedding(request.query)
    
    results = []
    
    if query_embedding:
        # Use vector similarity search with pgvector
        # <=> is the cosine distance operator (1 - similarity)
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        sql = text(f"""
            SELECT 
                id, title, summary, original_content, category, tags,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM knowledge
            WHERE is_archived = false AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        result = await db.execute(
            sql,
            {"embedding": embedding_str, "limit": limit}
        )
        
        for row in result.fetchall():
            snippet = row.summary or row.original_content[:200] + "..."
            results.append(SearchResult(
                id=row.id,
                title=row.title,
                summary=row.summary,
                category=row.category,
                tags=row.tags or [],
                similarity=round(float(row.similarity), 4),
                snippet=snippet
            ))
    
    # Fallback to text search if no vector results or no embedding
    if not results:
        # Use PostgreSQL full-text search as fallback
        search_pattern = f"%{request.query}%"
        
        stmt = (
            select(Knowledge)
            .where(Knowledge.is_archived == False)
            .where(
                Knowledge.title.ilike(search_pattern) |
                Knowledge.summary.ilike(search_pattern) |
                Knowledge.original_content.ilike(search_pattern)
            )
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        knowledge_items = result.scalars().all()
        
        for k in knowledge_items:
            snippet = k.summary or k.original_content[:200] + "..."
            results.append(SearchResult(
                id=k.id,
                title=k.title,
                summary=k.summary,
                category=k.category,
                tags=k.tags or [],
                similarity=0.5,  # Placeholder for text search
                snippet=snippet
            ))
    
    # Generate AI answer if requested
    answer = None
    if request.include_answer and results and settings.ai_configured:
        # Build context from top results
        context = "\n\n".join([
            f"【{r.title}】\n{r.snippet}"
            for r in results[:5]
        ])
        answer = await ai_service.answer_question(request.query, context)
    
    return SearchResponse(
        query=request.query,
        results=results,
        answer=answer,
        total=len(results)
    )


@router.get("/similar/{knowledge_id}")
async def find_similar(
    knowledge_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Find knowledge entries similar to the given one"""
    
    # Get the source knowledge
    result = await db.execute(
        select(Knowledge).where(Knowledge.id == knowledge_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    if not source.embedding:
        raise HTTPException(status_code=400, detail="Knowledge has no embedding")
    
    # Find similar using vector distance
    embedding_str = "[" + ",".join(map(str, source.embedding)) + "]"
    
    sql = text(f"""
        SELECT 
            id, title, summary, category, tags,
            1 - (embedding <=> :embedding::vector) as similarity
        FROM knowledge
        WHERE id != :source_id 
          AND is_archived = false 
          AND embedding IS NOT NULL
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
    """)
    
    result = await db.execute(
        sql,
        {"embedding": embedding_str, "source_id": knowledge_id, "limit": limit}
    )
    
    similar = []
    for row in result.fetchall():
        similar.append({
            "id": row.id,
            "title": row.title,
            "summary": row.summary,
            "category": row.category,
            "tags": row.tags or [],
            "similarity": round(float(row.similarity), 4)
        })
    
    return {
        "source_id": knowledge_id,
        "source_title": source.title,
        "similar": similar
    }

