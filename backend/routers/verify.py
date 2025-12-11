"""
Knowledge Verification API Router
知识验证系统 - 通过搜索和交叉引用验证知识的准确性
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, update
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.knowledge import Knowledge
from services.ai_service import ai_service
from services.embedding_service import embedding_service
from services.telegram_service import get_telegram_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/verify", tags=["Verification"])


class VerificationResult(BaseModel):
    """验证结果"""
    knowledge_id: int
    is_verified: bool
    confidence: float  # 0-1
    supporting_evidence: List[Dict[str, Any]]
    conflicting_evidence: List[Dict[str, Any]]
    verification_summary: str
    verified_at: str


class VerifyRequest(BaseModel):
    """验证请求"""
    knowledge_id: int
    auto_tag: bool = True  # 自动添加验证标签


async def _notify_telegram(message: str):
    """发送 Telegram 通知"""
    try:
        service = get_telegram_service()
        if service and service.enabled and service.chat_id:
            await service.send_message(message)
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


@router.post("/knowledge/{knowledge_id}", response_model=VerificationResult)
async def verify_knowledge(
    knowledge_id: int,
    auto_tag: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    验证知识条目的准确性
    
    验证流程：
    1. 提取知识的核心声明/关键点
    2. 在知识库中搜索相关证据
    3. 使用 AI 分析证据是否支持或反驳
    4. 计算置信度分数
    5. 如果验证通过，添加 "已验证" 标签
    """
    # 获取知识条目
    result = await db.execute(
        select(Knowledge).where(Knowledge.id == knowledge_id)
    )
    knowledge = result.scalar_one_or_none()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    
    await _notify_telegram(f"🔍 开始验证知识 #{knowledge_id}: {knowledge.title[:50]}...")
    
    # 提取关键声明用于验证
    claims_to_verify = knowledge.key_points or []
    if not claims_to_verify:
        claims_to_verify = [knowledge.summary or knowledge.original_content[:500]]
    
    supporting_evidence = []
    conflicting_evidence = []
    
    # 对每个关键点进行验证
    for claim in claims_to_verify[:5]:  # 最多验证5个关键点
        # 搜索相关知识
        if knowledge.embedding:
            # 使用向量搜索
            embedding_str = "[" + ",".join(map(str, knowledge.embedding)) + "]"
            
            sql = text("""
                SELECT 
                    id, title, summary, original_content, tags,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM knowledge
                WHERE id != :source_id 
                  AND is_archived = false 
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> :embedding::vector) >= 0.5
                ORDER BY embedding <=> :embedding::vector
                LIMIT 5
            """)
            
            search_result = await db.execute(
                sql,
                {"embedding": embedding_str, "source_id": knowledge_id}
            )
            
            related_knowledge = search_result.fetchall()
            
            for rk in related_knowledge:
                # 使用 AI 判断是否支持
                evidence_context = f"""
                待验证声明: {claim}
                
                相关知识: {rk.title}
                内容: {rk.summary or rk.original_content[:300]}
                """
                
                analysis = await ai_service.analyze_evidence(claim, rk.summary or rk.original_content[:500])
                
                evidence_item = {
                    "source_id": rk.id,
                    "source_title": rk.title,
                    "similarity": round(float(rk.similarity), 3),
                    "relation": analysis.get("relation", "neutral"),
                    "explanation": analysis.get("explanation", "")
                }
                
                if analysis.get("relation") == "supports":
                    supporting_evidence.append(evidence_item)
                elif analysis.get("relation") == "conflicts":
                    conflicting_evidence.append(evidence_item)
    
    # 计算置信度
    total_evidence = len(supporting_evidence) + len(conflicting_evidence)
    if total_evidence == 0:
        confidence = 0.5  # 无法验证，中等置信度
        is_verified = False
        verification_summary = "无法找到足够的相关知识进行验证"
    else:
        support_ratio = len(supporting_evidence) / total_evidence
        confidence = support_ratio
        
        if confidence >= 0.7 and len(supporting_evidence) >= 2:
            is_verified = True
            verification_summary = f"验证通过：找到 {len(supporting_evidence)} 条支持证据，{len(conflicting_evidence)} 条冲突证据"
        elif confidence >= 0.5:
            is_verified = False
            verification_summary = f"需要进一步验证：支持/冲突证据比例为 {support_ratio:.0%}"
        else:
            is_verified = False
            verification_summary = f"验证未通过：存在较多冲突证据"
    
    # 更新知识标签
    if auto_tag and is_verified:
        current_tags = knowledge.tags or []
        if "已验证" not in current_tags:
            current_tags.append("已验证")
            await db.execute(
                update(Knowledge)
                .where(Knowledge.id == knowledge_id)
                .values(tags=current_tags)
            )
            await db.commit()
            await _notify_telegram(f"✅ 知识 #{knowledge_id} 验证通过！已添加「已验证」标签")
    else:
        await _notify_telegram(f"⚠️ 知识 #{knowledge_id} 验证结果: {verification_summary}")
    
    return VerificationResult(
        knowledge_id=knowledge_id,
        is_verified=is_verified,
        confidence=round(confidence, 2),
        supporting_evidence=supporting_evidence,
        conflicting_evidence=conflicting_evidence,
        verification_summary=verification_summary,
        verified_at=datetime.utcnow().isoformat()
    )


@router.post("/batch")
async def verify_batch(
    knowledge_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """批量验证多个知识条目"""
    results = []
    for kid in knowledge_ids[:10]:  # 最多10个
        try:
            result = await verify_knowledge(kid, auto_tag=True, db=db)
            results.append(result)
        except Exception as e:
            results.append({
                "knowledge_id": kid,
                "error": str(e)
            })
    
    return {
        "total": len(results),
        "verified_count": sum(1 for r in results if isinstance(r, VerificationResult) and r.is_verified),
        "results": results
    }


@router.get("/status/{knowledge_id}")
async def get_verification_status(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取知识的验证状态"""
    result = await db.execute(
        select(Knowledge).where(Knowledge.id == knowledge_id)
    )
    knowledge = result.scalar_one_or_none()
    
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    
    tags = knowledge.tags or []
    
    return {
        "knowledge_id": knowledge_id,
        "is_verified": "已验证" in tags,
        "tags": tags,
        "can_verify": knowledge.embedding is not None
    }

