"""
Knowledge Graph API Router
知识图谱数据接口 - 用于可视化知识关联
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from database import get_db
from models.knowledge import Knowledge
from services.embedding_service import embedding_service

router = APIRouter(prefix="/api/v1/graph", tags=["Graph"])


class GraphNode(BaseModel):
    """图谱节点"""
    id: str
    label: str
    type: str  # category, knowledge, tag
    size: int = 20
    color: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class GraphEdge(BaseModel):
    """图谱边（关联）"""
    source: str
    target: str
    weight: float = 1.0
    type: str = "related"  # related, tagged, categorized


class GraphData(BaseModel):
    """完整图谱数据"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, Any]


@router.get("/data", response_model=GraphData)
async def get_graph_data(
    include_tags: bool = Query(True, description="包含标签节点"),
    include_categories: bool = Query(True, description="包含分类节点"),
    similarity_threshold: float = Query(0.7, description="相似度阈值"),
    limit: int = Query(100, description="最大知识点数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取知识图谱数据
    
    返回节点和边的数据，用于前端可视化：
    - 知识点节点
    - 分类节点
    - 标签节点
    - 知识点之间的相似度关联
    - 知识点与分类/标签的关联
    """
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    
    # Category colors
    category_colors = {
        "技术": "#58a6ff",
        "生活": "#3fb950",
        "商业": "#f0883e",
        "科学": "#a371f7",
        "学习": "#f778ba",
        "未分类": "#8b949e"
    }
    
    # 获取所有知识点
    result = await db.execute(
        select(Knowledge)
        .where(Knowledge.is_archived == False)
        .order_by(Knowledge.created_at.desc())
        .limit(limit)
    )
    knowledge_list = result.scalars().all()
    
    # 统计数据
    categories_count: Dict[str, int] = {}
    tags_count: Dict[str, int] = {}
    
    # 添加知识点节点
    for k in knowledge_list:
        # 计算节点大小（基于关键点数量和标签数量）
        size = 20 + len(k.key_points or []) * 3 + len(k.tags or []) * 2
        
        category = k.category or "未分类"
        categories_count[category] = categories_count.get(category, 0) + 1
        
        nodes.append(GraphNode(
            id=f"k_{k.id}",
            label=k.title[:30] + ("..." if len(k.title) > 30 else ""),
            type="knowledge",
            size=min(size, 50),
            color=category_colors.get(category, "#8b949e"),
            data={
                "id": k.id,
                "title": k.title,
                "summary": k.summary[:100] if k.summary else "",
                "category": category,
                "tags": k.tags or [],
                "is_verified": k.is_processed,  # 可以用 is_processed 或添加新字段
                "difficulty": k.difficulty
            }
        ))
        
        # 统计标签
        for tag in (k.tags or []):
            tags_count[tag] = tags_count.get(tag, 0) + 1
    
    # 添加分类节点
    if include_categories:
        for cat, count in categories_count.items():
            nodes.append(GraphNode(
                id=f"cat_{cat}",
                label=cat,
                type="category",
                size=30 + count * 5,
                color=category_colors.get(cat, "#8b949e"),
                data={"count": count}
            ))
            
            # 添加知识点到分类的边
            for k in knowledge_list:
                if (k.category or "未分类") == cat:
                    edges.append(GraphEdge(
                        source=f"k_{k.id}",
                        target=f"cat_{cat}",
                        weight=0.3,
                        type="categorized"
                    ))
    
    # 添加标签节点（只添加出现次数 >= 2 的标签）
    if include_tags:
        for tag, count in tags_count.items():
            if count >= 2:  # 至少出现2次
                nodes.append(GraphNode(
                    id=f"tag_{tag}",
                    label=f"#{tag}",
                    type="tag",
                    size=15 + count * 3,
                    color="#f0883e",
                    data={"count": count}
                ))
                
                # 添加知识点到标签的边
                for k in knowledge_list:
                    if tag in (k.tags or []):
                        edges.append(GraphEdge(
                            source=f"k_{k.id}",
                            target=f"tag_{tag}",
                            weight=0.5,
                            type="tagged"
                        ))
    
    # 查找知识点之间的相似关联（基于向量相似度）
    knowledge_with_embeddings = [k for k in knowledge_list if k.embedding is not None]
    
    if len(knowledge_with_embeddings) >= 2:
        # 对每个知识点找最相似的
        for k in knowledge_with_embeddings[:30]:  # 限制计算量
            embedding_str = "[" + ",".join(map(str, k.embedding)) + "]"
            
            sql = text("""
                SELECT 
                    id, title,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM knowledge
                WHERE id != :source_id 
                  AND is_archived = false 
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> :embedding::vector) >= :threshold
                ORDER BY embedding <=> :embedding::vector
                LIMIT 3
            """)
            
            result = await db.execute(
                sql,
                {
                    "embedding": embedding_str, 
                    "source_id": k.id, 
                    "threshold": similarity_threshold
                }
            )
            
            for row in result.fetchall():
                edges.append(GraphEdge(
                    source=f"k_{k.id}",
                    target=f"k_{row.id}",
                    weight=float(row.similarity),
                    type="related"
                ))
    
    return GraphData(
        nodes=nodes,
        edges=edges,
        stats={
            "total_knowledge": len(knowledge_list),
            "total_categories": len(categories_count),
            "total_tags": len(tags_count),
            "categories": categories_count,
            "top_tags": dict(sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:20])
        }
    )


@router.get("/connections/{knowledge_id}")
async def get_knowledge_connections(
    knowledge_id: int,
    depth: int = Query(1, ge=1, le=3, description="关联深度"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定知识点的关联网络
    
    用于在详情页展示相关知识
    """
    # 获取源知识点
    result = await db.execute(
        select(Knowledge).where(Knowledge.id == knowledge_id)
    )
    source = result.scalar_one_or_none()
    
    if not source:
        return {"error": "Knowledge not found"}
    
    connections = {
        "source": {
            "id": source.id,
            "title": source.title,
            "category": source.category,
            "tags": source.tags or []
        },
        "by_category": [],
        "by_tags": [],
        "by_similarity": []
    }
    
    # 同分类的知识点
    if source.category:
        result = await db.execute(
            select(Knowledge)
            .where(Knowledge.category == source.category)
            .where(Knowledge.id != knowledge_id)
            .where(Knowledge.is_archived == False)
            .limit(5)
        )
        connections["by_category"] = [
            {"id": k.id, "title": k.title, "summary": k.summary[:100] if k.summary else ""}
            for k in result.scalars().all()
        ]
    
    # 共享标签的知识点
    if source.tags:
        for tag in source.tags[:3]:  # 只查前3个标签
            result = await db.execute(
                select(Knowledge)
                .where(Knowledge.tags.contains([tag]))
                .where(Knowledge.id != knowledge_id)
                .where(Knowledge.is_archived == False)
                .limit(3)
            )
            for k in result.scalars().all():
                if not any(c["id"] == k.id for c in connections["by_tags"]):
                    connections["by_tags"].append({
                        "id": k.id, 
                        "title": k.title, 
                        "common_tag": tag
                    })
    
    # 向量相似的知识点
    if source.embedding:
        embedding_str = "[" + ",".join(map(str, source.embedding)) + "]"
        
        sql = text("""
            SELECT 
                id, title, summary,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM knowledge
            WHERE id != :source_id 
              AND is_archived = false 
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT 5
        """)
        
        result = await db.execute(
            sql,
            {"embedding": embedding_str, "source_id": knowledge_id}
        )
        
        connections["by_similarity"] = [
            {
                "id": row.id,
                "title": row.title,
                "summary": row.summary[:100] if row.summary else "",
                "similarity": round(float(row.similarity), 3)
            }
            for row in result.fetchall()
        ]
    
    return connections

