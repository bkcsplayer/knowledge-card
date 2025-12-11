"""
Telegram API Router
Telegram Bot 测试和状态接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.telegram_service import get_telegram_service, init_telegram_service
from config import settings

router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])


class SetChatIdRequest(BaseModel):
    """设置 Chat ID 请求"""
    chat_id: str


class TestMessageRequest(BaseModel):
    """测试消息请求"""
    message: str = "🧪 这是一条测试消息，来自 Knowledge Distillery！"


@router.get("/status")
async def get_telegram_status():
    """获取 Telegram 服务状态"""
    service = get_telegram_service()
    
    if not service:
        return {
            "status": "not_initialized",
            "configured": settings.telegram_configured,
            "has_token": bool(settings.telegram_bot_token),
            "has_chat_id": bool(settings.telegram_chat_id),
            "message": "请先配置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID"
        }
    
    # 测试连接
    connection_result = await service.test_connection()
    
    return {
        "status": connection_result.get("status"),
        "bot_name": connection_result.get("bot_name"),
        "bot_username": connection_result.get("bot_username"),
        "configured": settings.telegram_configured,
        "chat_id_set": bool(settings.telegram_chat_id),
        "message": connection_result.get("message")
    }


@router.post("/test")
async def send_test_message(request: TestMessageRequest):
    """发送测试消息到 Telegram"""
    service = get_telegram_service()
    
    if not service:
        raise HTTPException(status_code=400, detail="Telegram service not initialized")
    
    if not settings.telegram_chat_id:
        raise HTTPException(
            status_code=400, 
            detail="请先设置 TELEGRAM_CHAT_ID。发送任意消息给机器人，然后调用 /api/v1/telegram/get-updates 获取你的 chat_id"
        )
    
    success = await service.send_message(request.message)
    
    if success:
        return {"status": "success", "message": "测试消息已发送"}
    else:
        raise HTTPException(status_code=500, detail="发送消息失败")


@router.get("/get-updates")
async def get_bot_updates():
    """
    获取 Bot 收到的最近消息，用于找到你的 Chat ID
    
    步骤：
    1. 在 Telegram 中搜索你的 Bot 并发送任意消息
    2. 调用此接口获取 chat_id
    3. 将 chat_id 配置到 .env 文件中
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not configured")
    
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Telegram API error")
            
            data = response.json()
            updates = data.get("result", [])
            
            # 提取 chat 信息
            chats = []
            for update in updates:
                message = update.get("message", {})
                chat = message.get("chat", {})
                if chat:
                    chat_info = {
                        "chat_id": chat.get("id"),
                        "type": chat.get("type"),
                        "username": chat.get("username"),
                        "first_name": chat.get("first_name"),
                        "message_text": message.get("text", "")[:50]
                    }
                    if chat_info not in chats:
                        chats.append(chat_info)
            
            if not chats:
                return {
                    "status": "no_messages",
                    "message": "没有收到消息。请先在 Telegram 中向 Bot 发送任意消息，然后再调用此接口。",
                    "bot_token_preview": settings.telegram_bot_token[:10] + "..."
                }
            
            return {
                "status": "success",
                "message": "找到以下聊天，请将对应的 chat_id 配置到 .env 文件",
                "chats": chats,
                "next_step": "将 chat_id 添加到 .env: TELEGRAM_CHAT_ID=你的chat_id"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/test-flow")
async def test_notification_flow():
    """测试完整的通知流程"""
    service = get_telegram_service()
    
    if not service or not settings.telegram_chat_id:
        raise HTTPException(
            status_code=400, 
            detail="Telegram not fully configured. Need both token and chat_id"
        )
    
    # 模拟知识处理流程的通知
    import asyncio
    
    # 1. 创建通知
    await service.notify_knowledge_created(
        knowledge_id=999,
        title="测试知识条目",
        source_type="image"
    )
    await asyncio.sleep(1)
    
    # 2. 步骤通知
    await service.notify_step_start(999, "validating", "正在验证内容...")
    await asyncio.sleep(0.5)
    
    await service.notify_step_complete(999, "validating", "内容验证通过")
    await asyncio.sleep(0.5)
    
    await service.notify_step_start(999, "analyzing_images", "正在分析图片...")
    await asyncio.sleep(1)
    
    await service.notify_step_complete(999, "analyzing_images", "图片分析完成", "检测到: Web3 学习路线图")
    await asyncio.sleep(0.5)
    
    await service.notify_step_start(999, "distilling", "AI 正在蒸馏知识...")
    await asyncio.sleep(1)
    
    await service.notify_step_complete(999, "distilling", "知识蒸馏完成")
    await asyncio.sleep(0.5)
    
    # 3. 完成通知
    await service.notify_knowledge_completed(
        knowledge_id=999,
        title="Web3 完整学习路线图",
        summary="这是一份系统的 Web3 学习指南，涵盖智能合约开发、DeFi 协议研究等...",
        tags=["Web3", "区块链", "DeFi", "智能合约"]
    )
    
    return {"status": "success", "message": "测试通知流程已发送，请检查 Telegram"}

