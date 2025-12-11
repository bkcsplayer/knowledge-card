"""
Telegram Bot Notification Service
实时状态反馈系统 - 通过 Telegram 发送处理状态通知
"""

import httpx
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram Bot 通知服务"""
    
    def __init__(self, bot_token: str, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token)
    
    async def send_message(self, text: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> bool:
        """发送消息到 Telegram"""
        if not self.enabled:
            logger.warning("Telegram service not enabled (no bot token)")
            return False
        
        target_chat = chat_id or self.chat_id
        if not target_chat:
            logger.warning("No chat_id specified for Telegram message")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": target_chat,
                        "text": text,
                        "parse_mode": parse_mode
                    }
                )
                
                if response.status_code == 200:
                    logger.info(f"Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def notify_knowledge_created(self, knowledge_id: int, title: str, source_type: str):
        """通知：知识条目已创建"""
        text = f"""
🆕 <b>新知识创建</b>

📋 ID: <code>{knowledge_id}</code>
📝 标题: {title[:50]}...
📦 类型: {source_type}
⏰ 时间: {datetime.now().strftime('%H:%M:%S')}

<i>开始处理中...</i>
"""
        await self.send_message(text)
    
    async def notify_step_start(self, knowledge_id: int, step: str, message: str):
        """通知：步骤开始"""
        emoji_map = {
            "validating": "🔍",
            "analyzing_images": "📷",
            "distilling": "🧪",
            "embedding": "🔗",
        }
        emoji = emoji_map.get(step, "⏳")
        
        text = f"{emoji} <b>#{knowledge_id}</b> | {message}"
        await self.send_message(text)
    
    async def notify_step_complete(self, knowledge_id: int, step: str, message: str, details: Optional[str] = None):
        """通知：步骤完成"""
        text = f"✅ <b>#{knowledge_id}</b> | {message}"
        if details:
            text += f"\n<i>{details[:200]}</i>"
        await self.send_message(text)
    
    async def notify_step_failed(self, knowledge_id: int, step: str, error: str):
        """通知：步骤失败"""
        text = f"""
❌ <b>处理失败</b>

📋 ID: <code>{knowledge_id}</code>
🔧 步骤: {step}
💥 错误: <code>{error[:300]}</code>
⏰ 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text)
    
    async def notify_knowledge_completed(self, knowledge_id: int, title: str, summary: str, tags: list):
        """通知：知识处理完成"""
        tags_str = ", ".join(tags[:5]) if tags else "无标签"
        
        text = f"""
🎉 <b>处理完成</b>

📋 ID: <code>{knowledge_id}</code>
📝 标题: <b>{title[:100]}</b>
🏷️ 标签: {tags_str}

📄 摘要:
<i>{summary[:300]}...</i>

⏰ 完成时间: {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text)
    
    async def notify_system_status(self, status: str, details: str):
        """通知：系统状态"""
        text = f"""
🖥️ <b>系统状态</b>

状态: {status}
详情: {details}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(text)
    
    async def test_connection(self) -> dict:
        """测试 Telegram 连接"""
        if not self.enabled:
            return {"status": "disabled", "message": "Bot token not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/getMe")
                
                if response.status_code == 200:
                    data = response.json()
                    bot_info = data.get("result", {})
                    return {
                        "status": "connected",
                        "bot_name": bot_info.get("first_name"),
                        "bot_username": bot_info.get("username"),
                        "message": "Telegram bot connected successfully"
                    }
                else:
                    return {"status": "error", "message": f"API error: {response.status_code}"}
                    
        except Exception as e:
            return {"status": "error", "message": str(e)}


# 全局实例（将在 config 加载后初始化）
telegram_service: Optional[TelegramService] = None


def init_telegram_service(bot_token: str, chat_id: str) -> TelegramService:
    """初始化 Telegram 服务"""
    global telegram_service
    telegram_service = TelegramService(bot_token, chat_id)
    logger.info(f"Telegram service initialized (enabled: {telegram_service.enabled})")
    return telegram_service


def get_telegram_service() -> Optional[TelegramService]:
    """获取 Telegram 服务实例"""
    return telegram_service

