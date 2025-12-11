"""
Knowledge API Router
CRUD endpoints for knowledge management
Supports: text content, URL, images, files
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.knowledge_service import knowledge_service

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge"])


# Request/Response Models
class KnowledgeCreate(BaseModel):
    """
    Create knowledge request
    
    支持多种输入方式（至少提供一种）：
    - content: 文本内容
    - source_url: 网页 URL（未来支持自动抓取）
    - images: 图片路径列表（AI 将分析图片内容）
    """
    content: Optional[str] = ""  # 文本内容（可选）
    title: Optional[str] = None
    source_type: str = "manual"  # manual, url, image, file
    source_url: Optional[str] = None  # URL 来源
    images: Optional[List[str]] = None  # 图片路径列表
    auto_process: bool = True


class KnowledgeUpdate(BaseModel):
    """Update knowledge request"""
    title: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    action_items: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class KnowledgeResponse(BaseModel):
    """Knowledge response model"""
    id: int
    title: str
    original_content: str
    summary: Optional[str]
    key_points: List[str]
    tags: List[str]
    category: Optional[str]
    difficulty: Optional[str]
    action_items: List[str]
    usage_example: Optional[str] = None
    deployment_guide: Optional[str] = None
    is_open_source: bool = False
    repo_url: Optional[str] = None
    images: List[str] = []
    processing_status: str = "pending"
    processing_steps: List[Dict[str, Any]] = []
    source_type: str
    source_url: Optional[str]
    is_processed: bool
    is_archived: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    processed_at: Optional[str]
    
    class Config:
        from_attributes = True


# Endpoints
@router.post("/", response_model=KnowledgeResponse)
async def create_knowledge(
    request: KnowledgeCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new knowledge entry
    
    支持多种输入方式（至少提供一种）：
    - **content**: 文本内容（可以为空，如果提供了图片）
    - **source_url**: URL 来源
    - **images**: 图片路径列表，AI 将自动分析图片内容
    - **source_type**: 来源类型 (manual, url, image, file)
    - **auto_process**: 是否自动 AI 处理（默认: true）
    
    示例：
    1. 仅文本: {"content": "你的内容..."}
    2. 仅图片: {"images": ["/api/v1/upload/images/xxx.jpg"], "source_type": "image"}
    3. 文本+图片: {"content": "补充说明", "images": ["..."]}
    """
    # 验证：至少要有 content 或 images
    has_content = request.content and len(request.content.strip()) > 0
    has_images = request.images and len(request.images) > 0
    has_url = request.source_url and len(request.source_url.strip()) > 0
    
    if not has_content and not has_images and not has_url:
        raise HTTPException(
            status_code=400, 
            detail="请提供内容、图片或 URL 中的至少一项"
        )
    
    # 根据输入自动判断 source_type
    if has_images and not has_content:
        source_type = "image"
    elif has_url and not has_content:
        source_type = "url"
    else:
        source_type = request.source_type
    
    knowledge = await knowledge_service.create(
        db=db,
        content=request.content or "",
        title=request.title,
        source_type=source_type,
        source_url=request.source_url,
        images=request.images,
        auto_process=request.auto_process
    )
    
    return knowledge.to_dict()


@router.get("/", response_model=List[KnowledgeResponse])
async def list_knowledge(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    List all knowledge entries with optional filtering
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum records to return (1-100)
    - **category**: Filter by category
    - **tag**: Filter by tag
    - **search**: Search in title, content, and summary
    - **include_archived**: Include archived entries
    """
    entries = await knowledge_service.get_all(
        db=db,
        skip=skip,
        limit=limit,
        category=category,
        tag=tag,
        search=search,
        include_archived=include_archived
    )
    
    return [k.to_dict() for k in entries]


@router.get("/stats")
async def get_knowledge_stats(db: AsyncSession = Depends(get_db)):
    """Get knowledge base statistics"""
    return await knowledge_service.get_stats(db)


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific knowledge entry by ID"""
    knowledge = await knowledge_service.get_by_id(db, knowledge_id)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    return knowledge.to_dict()


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    knowledge_id: int,
    request: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a knowledge entry"""
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    knowledge = await knowledge_service.update(db, knowledge_id, updates)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    return knowledge.to_dict()


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge entry permanently"""
    success = await knowledge_service.delete(db, knowledge_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    return {"status": "deleted", "id": knowledge_id}


@router.post("/{knowledge_id}/archive")
async def archive_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Archive a knowledge entry (soft delete)"""
    knowledge = await knowledge_service.archive(db, knowledge_id)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    
    return {"status": "archived", "id": knowledge_id}


@router.post("/{knowledge_id}/reprocess")
async def reprocess_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Re-process a knowledge entry with AI"""
    try:
        knowledge = await knowledge_service.process_with_ai(db, knowledge_id)
        return knowledge.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
