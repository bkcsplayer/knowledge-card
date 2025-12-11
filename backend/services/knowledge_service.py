"""
Knowledge Service
Handles CRUD operations and AI processing for knowledge entries
Supports image analysis for screenshot-based knowledge creation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import Knowledge
from services.ai_service import ai_service
from services.embedding_service import embedding_service
import logging

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for managing knowledge entries"""
    
    async def create(
        self,
        db: AsyncSession,
        content: str = "",
        title: Optional[str] = None,
        source_type: str = "manual",
        source_url: Optional[str] = None,
        images: Optional[List[str]] = None,
        auto_process: bool = True
    ) -> Knowledge:
        """
        Create a new knowledge entry
        
        Args:
            db: Database session
            content: Raw content to store (can be empty if images provided)
            title: Optional title (will be auto-generated if not provided)
            source_type: Type of source (manual, url, file, api, image)
            source_url: URL of source if applicable
            images: List of image URLs/paths to analyze
            auto_process: Whether to automatically distill with AI
        
        Returns:
            Created Knowledge instance
        """
        # Validate: either content or images must be provided
        has_content = content and len(content.strip()) > 0
        has_images = images and len(images) > 0
        
        if not has_content and not has_images:
            raise ValueError("必须提供文本内容或图片")
        
        # Determine source type
        if has_images and not has_content:
            source_type = "image"
            initial_content = f"[图片内容待分析] 共 {len(images)} 张图片"
        else:
            initial_content = content
        
        # Create initial entry with pending status
        knowledge = Knowledge(
            title=title or (initial_content[:80] + "..." if len(initial_content) > 80 else initial_content),
            original_content=initial_content,
            source_type=source_type,
            source_url=source_url,
            images=images or [],
            is_processed=False,
            processing_status="pending",
            processing_steps=[{
                "step": "created",
                "status": "completed",
                "message": f"知识条目已创建 {'(含图片)' if has_images else ''}",
                "timestamp": datetime.utcnow().isoformat()
            }]
        )
        
        db.add(knowledge)
        await db.commit()
        await db.refresh(knowledge)
        
        logger.info(f"Created knowledge {knowledge.id}: has_content={has_content}, has_images={has_images}")
        
        # Auto-process with AI if requested
        if auto_process:
            knowledge = await self.process_with_ai(db, knowledge.id)
        
        return knowledge
    
    async def process_with_ai(self, db: AsyncSession, knowledge_id: int) -> Knowledge:
        """
        Process a knowledge entry with AI to extract insights
        Supports image analysis for screenshot-based content
        
        Args:
            db: Database session
            knowledge_id: ID of knowledge to process
        
        Returns:
            Updated Knowledge instance
        """
        # Get knowledge entry
        result = await db.execute(
            select(Knowledge).where(Knowledge.id == knowledge_id)
        )
        knowledge = result.scalar_one_or_none()
        
        if not knowledge:
            raise ValueError(f"Knowledge {knowledge_id} not found")
        
        steps = knowledge.processing_steps or []
        has_images = knowledge.images and len(knowledge.images) > 0
        
        # Step 1: Validating
        knowledge.processing_status = "validating"
        steps.append({
            "step": "validating",
            "status": "completed",
            "message": "内容验证通过",
            "timestamp": datetime.utcnow().isoformat()
        })
        knowledge.processing_steps = steps
        await db.commit()
        
        # Step 2: Image Analysis (if applicable)
        if has_images:
            knowledge.processing_status = "analyzing_images"
            steps.append({
                "step": "analyzing_images",
                "status": "in_progress",
                "message": f"正在分析 {len(knowledge.images)} 张图片...",
                "timestamp": datetime.utcnow().isoformat()
            })
            knowledge.processing_steps = steps
            await db.commit()
            
            logger.info(f"Analyzing {len(knowledge.images)} images for knowledge {knowledge.id}")
        
        # Step 3: Distilling with AI (handles both text and images)
        knowledge.processing_status = "distilling"
        steps.append({
            "step": "distilling",
            "status": "in_progress",
            "message": "AI 正在蒸馏知识..." + (" (含图片分析)" if has_images else ""),
            "timestamp": datetime.utcnow().isoformat()
        })
        knowledge.processing_steps = steps
        await db.commit()
        
        # Get content - if source is image-only, pass empty string
        content_for_distill = knowledge.original_content
        if knowledge.source_type == "image":
            content_for_distill = ""  # Let AI extract from images
        
        # Distill with AI - pass images for analysis
        distilled = await ai_service.distill_knowledge(
            content=content_for_distill,
            context=None,
            images=knowledge.images if has_images else None
        )
        
        # Check if there was an error
        if distilled.get("error"):
            steps.append({
                "step": "distilling",
                "status": "failed",
                "message": distilled.get("error", "蒸馏失败"),
                "timestamp": datetime.utcnow().isoformat()
            })
            knowledge.processing_status = "failed"
            knowledge.processing_steps = steps
            knowledge.title = distilled.get("title", "处理失败")
            knowledge.summary = distilled.get("summary", "内容无法处理")
            await db.commit()
            await db.refresh(knowledge)
            return knowledge
        
        # Update with distilled results
        knowledge.title = distilled.get("title", knowledge.title)
        knowledge.summary = distilled.get("summary", "")
        knowledge.key_points = distilled.get("key_points", [])
        knowledge.tags = distilled.get("tags", [])
        knowledge.category = distilled.get("category", "未分类")
        knowledge.difficulty = distilled.get("difficulty", "未知")
        knowledge.action_items = distilled.get("action_items", [])
        knowledge.usage_example = distilled.get("usage_example")
        knowledge.deployment_guide = distilled.get("deployment_guide")
        knowledge.is_open_source = distilled.get("is_open_source", False)
        knowledge.repo_url = distilled.get("repo_url")
        
        # If we extracted content from images, update original_content
        if knowledge.source_type == "image" and distilled.get("summary"):
            # Store the AI-extracted content as reference
            knowledge.original_content = f"[从图片提取的内容]\n\n{distilled.get('summary', '')}\n\n关键点:\n" + "\n".join(f"- {kp}" for kp in distilled.get('key_points', []))
        
        if has_images:
            steps.append({
                "step": "analyzing_images",
                "status": "completed",
                "message": "图片分析完成",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        steps.append({
            "step": "distilling",
            "status": "completed",
            "message": "知识蒸馏完成",
            "timestamp": datetime.utcnow().isoformat()
        })
        knowledge.processing_steps = steps
        
        # Step 4: Generate embedding
        knowledge.processing_status = "embedding"
        steps.append({
            "step": "embedding",
            "status": "in_progress",
            "message": "正在生成向量嵌入...",
            "timestamp": datetime.utcnow().isoformat()
        })
        knowledge.processing_steps = steps
        await db.commit()
        
        try:
            text_for_embedding = f"{knowledge.title}\n{knowledge.summary}\n{knowledge.original_content}"
            embedding = await embedding_service.get_embedding(text_for_embedding)
            if embedding:
                knowledge.embedding = embedding
                steps.append({
                    "step": "embedding",
                    "status": "completed",
                    "message": "向量嵌入生成成功",
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"Generated embedding for knowledge {knowledge.id}")
            else:
                steps.append({
                    "step": "embedding",
                    "status": "skipped",
                    "message": "向量嵌入跳过（API 未配置）",
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            steps.append({
                "step": "embedding",
                "status": "failed",
                "message": f"向量嵌入失败: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.warning(f"Failed to generate embedding: {e}")
        
        # Mark as completed
        knowledge.processing_status = "completed"
        knowledge.is_processed = True
        knowledge.processed_at = datetime.utcnow()
        
        steps.append({
            "step": "completed",
            "status": "completed",
            "message": "处理完成",
            "timestamp": datetime.utcnow().isoformat()
        })
        knowledge.processing_steps = steps
        
        await db.commit()
        await db.refresh(knowledge)
        
        logger.info(f"Completed processing knowledge {knowledge.id}: {knowledge.title}")
        
        return knowledge
    
    async def get_by_id(self, db: AsyncSession, knowledge_id: int) -> Optional[Knowledge]:
        """Get knowledge by ID"""
        result = await db.execute(
            select(Knowledge).where(Knowledge.id == knowledge_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False
    ) -> List[Knowledge]:
        """
        Get all knowledge entries with optional filtering
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            category: Filter by category
            tag: Filter by tag
            search: Search in title and content
            include_archived: Include archived entries
        
        Returns:
            List of Knowledge instances
        """
        query = select(Knowledge)
        
        # Filter archived
        if not include_archived:
            query = query.where(Knowledge.is_archived == False)
        
        # Filter by category
        if category:
            query = query.where(Knowledge.category == category)
        
        # Filter by tag
        if tag:
            query = query.where(Knowledge.tags.contains([tag]))
        
        # Search in title and content
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Knowledge.title.ilike(search_pattern),
                    Knowledge.original_content.ilike(search_pattern),
                    Knowledge.summary.ilike(search_pattern)
                )
            )
        
        # Order and paginate
        query = query.order_by(desc(Knowledge.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        db: AsyncSession,
        knowledge_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Knowledge]:
        """Update a knowledge entry"""
        knowledge = await self.get_by_id(db, knowledge_id)
        
        if not knowledge:
            return None
        
        # Update allowed fields
        allowed_fields = ["title", "summary", "key_points", "tags", "category", 
                        "difficulty", "action_items", "is_archived"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(knowledge, field, value)
        
        await db.commit()
        await db.refresh(knowledge)
        
        return knowledge
    
    async def delete(self, db: AsyncSession, knowledge_id: int) -> bool:
        """Delete a knowledge entry"""
        knowledge = await self.get_by_id(db, knowledge_id)
        
        if not knowledge:
            return False
        
        await db.delete(knowledge)
        await db.commit()
        
        return True
    
    async def archive(self, db: AsyncSession, knowledge_id: int) -> Optional[Knowledge]:
        """Archive a knowledge entry (soft delete)"""
        return await self.update(db, knowledge_id, {"is_archived": True})
    
    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        # Total count
        total_result = await db.execute(
            select(func.count(Knowledge.id)).where(Knowledge.is_archived == False)
        )
        total = total_result.scalar()
        
        # Count by category
        category_result = await db.execute(
            select(Knowledge.category, func.count(Knowledge.id))
            .where(Knowledge.is_archived == False)
            .group_by(Knowledge.category)
        )
        categories = {row[0] or "未分类": row[1] for row in category_result.all()}
        
        # Recent entries (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_result = await db.execute(
            select(func.count(Knowledge.id))
            .where(Knowledge.is_archived == False)
            .where(Knowledge.created_at >= week_ago)
        )
        recent = recent_result.scalar()
        
        # Processed count
        processed_result = await db.execute(
            select(func.count(Knowledge.id))
            .where(Knowledge.is_archived == False)
            .where(Knowledge.is_processed == True)
        )
        processed = processed_result.scalar()
        
        return {
            "total": total,
            "recent_7_days": recent,
            "processed": processed,
            "unprocessed": total - processed,
            "categories": categories
        }
    
    async def get_recent_for_digest(
        self,
        db: AsyncSession,
        days: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent knowledge entries for daily digest"""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(Knowledge)
            .where(Knowledge.is_archived == False)
            .where(Knowledge.is_processed == True)
            .where(Knowledge.created_at >= cutoff)
            .order_by(desc(Knowledge.created_at))
            .limit(limit)
        )
        
        entries = result.scalars().all()
        
        return [
            {
                "title": k.title,
                "summary": k.summary,
                "key_points": k.key_points or [],
                "tags": k.tags or [],
                "category": k.category
            }
            for k in entries
        ]


# Global service instance
knowledge_service = KnowledgeService()
