"""
AI Service for Knowledge Distillery
Handles knowledge distillation using OpenRouter API with Vision support
"""

import httpx
import json
import base64
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


class AIService:
    """OpenRouter AI Service for knowledge distillation with Vision support"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://knowledge-distillery.local",
            "X-Title": "Knowledge Distillery"
        }
    
    async def _call_api(self, messages: List[Dict], temperature: float = 0.7) -> Optional[str]:
        """Make async API call to OpenRouter"""
        if not settings.ai_configured:
            logger.warning("AI not configured - missing API key")
            return None
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return None
    
    async def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert local image file to base64"""
        try:
            # Handle different path formats
            if image_path.startswith('/api/v1/upload/images/'):
                # Extract filename and build local path
                # Docker container path: /app/uploads/images/filename
                filename = image_path.split('/')[-1]
                local_path = Path("/app/uploads/images") / filename
            elif image_path.startswith('http'):
                # Download remote image
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_path)
                    response.raise_for_status()
                    return base64.b64encode(response.content).decode('utf-8')
            elif image_path.startswith('/'):
                # Absolute path
                local_path = Path(image_path)
            else:
                # Relative path - try multiple locations
                local_path = Path("/app/uploads/images") / image_path
                if not local_path.exists():
                    local_path = Path("/app/uploads") / image_path
                if not local_path.exists():
                    local_path = Path(image_path)
            
            logger.info(f"Looking for image at: {local_path}")
            
            if local_path.exists():
                with open(local_path, 'rb') as f:
                    content = f.read()
                    logger.info(f"Successfully loaded image: {local_path} ({len(content)} bytes)")
                    return base64.b64encode(content).decode('utf-8')
            else:
                logger.warning(f"Image file not found: {local_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            return None
    
    async def _get_image_media_type(self, image_path: str) -> str:
        """Determine media type from image path"""
        ext = image_path.lower().split('.')[-1]
        media_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return media_types.get(ext, 'image/jpeg')
    
    async def analyze_image(self, image_paths: List[str], context: Optional[str] = None) -> Optional[str]:
        """
        Analyze image(s) and extract text/content description
        
        Args:
            image_paths: List of image file paths or URLs
            context: Optional context about what to look for
        
        Returns:
            Extracted text and description from images
        """
        if not settings.ai_configured:
            logger.warning("AI not configured - missing API key")
            return None
        
        # Build content with images
        content = []
        
        # Add text prompt first
        prompt = """请仔细分析这张/这些图片，并提取所有重要信息：

1. 如果是截图（网页、应用、代码等）：
   - 提取所有可见的文字内容
   - 描述界面布局和功能
   - 如果是开源项目页面，提取项目名、描述、特性等

2. 如果是代码截图：
   - 转录所有代码
   - 识别编程语言
   - 解释代码功能

3. 如果是文档/文章截图：
   - 提取完整文字内容
   - 保持原有结构

4. 如果是图表/架构图：
   - 详细描述图表内容
   - 解释各部分关系

请提供完整、详细的内容提取结果。"""
        
        if context:
            prompt = f"{context}\n\n{prompt}"
        
        content.append({"type": "text", "text": prompt})
        
        # Add images
        for image_path in image_paths:
            base64_image = await self._image_to_base64(image_path)
            if base64_image:
                media_type = await self._get_image_media_type(image_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_image}"
                    }
                })
            else:
                logger.warning(f"Could not load image: {image_path}")
        
        if len(content) == 1:  # Only text, no images loaded
            logger.error("No images could be loaded for analysis")
            return None
        
        messages = [
            {"role": "user", "content": content}
        ]
        
        result = await self._call_api(messages, temperature=0.3)
        return result
    
    async def distill_knowledge(
        self, 
        content: str, 
        context: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Distill knowledge from content and/or images
        
        Args:
            content: The raw text content to distill (can be empty if images provided)
            context: Optional context about the content type
            images: Optional list of image paths to analyze
        
        Returns:
            Dict with summary, key_points, tags, and other extracted info
        """
        # If we have images but no/little content, analyze images first
        actual_content = content
        
        if images and len(images) > 0:
            if not content or len(content.strip()) < 50:
                logger.info(f"Analyzing {len(images)} images for content extraction...")
                image_content = await self.analyze_image(images, context)
                if image_content:
                    actual_content = image_content
                    logger.info(f"Extracted {len(image_content)} chars from images")
                else:
                    return {
                        "error": "图片分析失败",
                        "title": "图片内容无法识别",
                        "summary": "无法从上传的图片中提取内容，请确保图片清晰可读。",
                        "key_points": [],
                        "tags": [],
                        "category": "未分类",
                        "difficulty": "未知",
                        "action_items": []
                    }
            else:
                # We have both content and images, analyze images and combine
                logger.info(f"Analyzing {len(images)} images to supplement content...")
                image_content = await self.analyze_image(images, context)
                if image_content:
                    actual_content = f"{content}\n\n---\n图片内容分析：\n{image_content}"
        
        if not actual_content or len(actual_content.strip()) < 10:
            return {
                "error": "内容为空",
                "title": "无法处理",
                "summary": "没有提供有效的内容或图片进行分析。",
                "key_points": [],
                "tags": [],
                "category": "未分类",
                "difficulty": "未知",
                "action_items": []
            }
        
        system_prompt = """你是一个专业的知识蒸馏专家。你的任务是将复杂的内容提炼成清晰、简洁的知识点。

请按照以下 JSON 格式输出（确保是有效的 JSON）：
{
    "title": "内容的简短标题",
    "summary": "100-200字的核心摘要",
    "key_points": ["关键点1", "关键点2", "关键点3"],
    "tags": ["标签1", "标签2", "标签3"],
    "category": "知识分类（如：技术、商业、科学、生活等）",
    "difficulty": "难度等级（简单/中等/困难）",
    "action_items": ["可执行的行动建议1", "行动建议2"],
    "usage_example": "如果是代码/工具/API，提供简单的使用示例代码或步骤，否则为null",
    "deployment_guide": "如果是开源项目或可部署的系统，提供部署步骤，否则为null",
    "is_open_source": false,
    "repo_url": "如果提到了GitHub/GitLab仓库地址，提取出来，否则为null"
}

注意：
- 提取最重要的3-5个关键点
- 标签应该简洁且有助于搜索
- 行动建议应该具体可执行
- 如果内容涉及代码、工具、API或框架，必须提供使用示例
- 如果是开源项目，必须提供部署指南
- 如果内容来自截图分析，确保提取关键信息"""

        user_prompt = f"""请蒸馏以下内容：

{f'上下文: {context}' if context else ''}

---
{actual_content}
---

请返回 JSON 格式的蒸馏结果。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = await self._call_api(messages, temperature=0.3)
        
        if not result:
            return {
                "error": "AI processing failed",
                "title": "未处理",
                "summary": actual_content[:200] + "..." if len(actual_content) > 200 else actual_content,
                "key_points": [],
                "tags": [],
                "category": "未分类",
                "difficulty": "未知",
                "action_items": []
            }
        
        try:
            # Try to parse JSON from response
            # Handle case where AI might wrap JSON in markdown code blocks
            cleaned = result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON: {result[:100]}")
            return {
                "title": "解析失败",
                "summary": result[:500],
                "key_points": [],
                "tags": [],
                "category": "未分类",
                "difficulty": "未知",
                "action_items": [],
                "raw_response": result
            }
    
    async def generate_daily_digest(self, knowledge_items: List[Dict]) -> Dict[str, Any]:
        """
        Generate a daily digest from multiple knowledge items
        
        Args:
            knowledge_items: List of distilled knowledge items
        
        Returns:
            Dict with digest content
        """
        if not knowledge_items:
            return {
                "title": f"每日知识摘要 - {datetime.now().strftime('%Y-%m-%d')}",
                "content": "今日暂无新知识入库。",
                "highlights": [],
                "stats": {"total": 0}
            }
        
        items_text = "\n\n".join([
            f"【{item.get('title', '未命名')}】\n{item.get('summary', '')}\n关键点: {', '.join(item.get('key_points', []))}"
            for item in knowledge_items[:10]  # Limit to 10 items
        ])
        
        system_prompt = """你是知识管理助手。请根据今日的知识条目生成一份简洁的每日摘要。

输出格式（JSON）：
{
    "title": "每日知识摘要标题",
    "overview": "今日知识的总体概述（50-100字）",
    "highlights": ["今日亮点1", "今日亮点2", "今日亮点3"],
    "connections": "知识之间的关联或模式（如果有的话）",
    "recommendation": "今日建议关注的重点"
}"""

        user_prompt = f"""今日收录的知识条目：

{items_text}

请生成每日摘要。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = await self._call_api(messages, temperature=0.5)
        
        if not result:
            return {
                "title": f"每日知识摘要 - {datetime.now().strftime('%Y-%m-%d')}",
                "overview": f"今日共收录 {len(knowledge_items)} 条知识。",
                "highlights": [item.get('title', '未命名') for item in knowledge_items[:3]],
                "stats": {"total": len(knowledge_items)}
            }
        
        try:
            cleaned = result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            digest = json.loads(cleaned.strip())
            digest["stats"] = {"total": len(knowledge_items)}
            return digest
        except json.JSONDecodeError:
            return {
                "title": f"每日知识摘要 - {datetime.now().strftime('%Y-%m-%d')}",
                "overview": result[:300],
                "highlights": [],
                "stats": {"total": len(knowledge_items)}
            }
    
    async def answer_question(self, question: str, context: Optional[str] = None) -> str:
        """
        Answer a question based on knowledge base context
        
        Args:
            question: User's question
            context: Relevant knowledge context from vector search
        
        Returns:
            AI-generated answer
        """
        system_prompt = """你是 Knowledge Distillery 的知识助手。基于提供的知识库内容回答用户问题。

规则：
1. 如果知识库中有相关信息，基于该信息回答
2. 如果信息不足，诚实说明并提供你知道的相关信息
3. 回答要简洁、准确、有帮助
4. 可以适当扩展，但要标注哪些是知识库内容，哪些是补充"""

        user_prompt = f"""问题：{question}

{'知识库相关内容：' + context if context else '（暂无相关知识库内容）'}

请回答用户问题。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        result = await self._call_api(messages, temperature=0.7)
        return result or "抱歉，AI 服务暂时不可用。请稍后再试。"
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the AI API connection"""
        if not settings.ai_configured:
            return {
                "status": "error",
                "message": "API key not configured",
                "configured": False
            }
        
        messages = [
            {"role": "user", "content": "Say 'Knowledge Distillery AI is ready!' in exactly those words."}
        ]
        
        result = await self._call_api(messages, temperature=0)
        
        if result:
            return {
                "status": "success",
                "message": result,
                "model": self.model,
                "configured": True
            }
        else:
            return {
                "status": "error",
                "message": "Failed to connect to OpenRouter API",
                "configured": True
            }


# Global AI service instance
ai_service = AIService()
