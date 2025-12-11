"""
Knowledge Distillation Pipeline
多阶段、多模型深度知识蒸馏系统

流程：
1. 提取阶段 (Extract) - 从原始内容/图片提取基础信息
2. 分析阶段 (Analyze) - 深度理解内容结构和技术细节
3. 搜索阶段 (Search) - 搜索相关信息补充上下文
4. 验证阶段 (Verify) - 交叉验证关键信息
5. 归纳阶段 (Synthesize) - 综合所有信息生成知识卡片
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.ai_service import ai_service
from services.telegram_service import get_telegram_service
from config import settings

logger = logging.getLogger(__name__)


class DistillationPipeline:
    """多阶段知识蒸馏管道"""
    
    def __init__(self):
        self.stages = [
            "extract",      # 提取
            "analyze",      # 分析
            "search",       # 搜索
            "verify",       # 验证
            "synthesize"    # 归纳
        ]
    
    async def _notify(self, message: str):
        """发送 Telegram 通知"""
        try:
            service = get_telegram_service()
            if service and service.enabled and service.chat_id:
                await service.send_message(message)
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
    
    async def run(
        self, 
        content: str = "", 
        images: Optional[List[str]] = None,
        knowledge_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        运行完整的蒸馏管道（带回退机制）
        
        Args:
            content: 原始文本内容
            images: 图片路径列表
            knowledge_id: 知识条目ID（用于通知）
        
        Returns:
            完整的知识卡片数据
        """
        kid = knowledge_id or 0
        
        # 首先尝试简化版的单次蒸馏（更可靠）
        await self._notify(f"🧪 #{kid} | 开始 AI 知识蒸馏...")
        
        try:
            result = await self._simple_distill(content, images, kid)
            if result and not result.get("error"):
                await self._notify(f"🎉 #{kid} | 蒸馏完成!\n📝 {result.get('title', '')[:50]}\n🏷️ {', '.join(result.get('tags', [])[:5])}")
                return result
        except Exception as e:
            logger.warning(f"Simple distill failed, trying pipeline: {e}")
        
        # 如果简化版失败，尝试多阶段管道
        await self._notify(f"⚙️ #{kid} | 启用多阶段深度分析...")
        
        pipeline_result = {
            "stages_completed": [],
            "raw_extractions": {},
            "final_result": None,
            "errors": []
        }
        
        try:
            # ========== 阶段 1: 提取 ==========
            extraction = await self._stage_extract(content, images)
            pipeline_result["raw_extractions"]["extract"] = extraction
            pipeline_result["stages_completed"].append("extract")
            
            if extraction.get("error"):
                raise Exception(f"提取失败: {extraction.get('error')}")
            
            await self._notify(f"✅ #{kid} | 提取完成")
            
            # ========== 阶段 2: 分析 ==========
            analysis = await self._stage_analyze(extraction)
            pipeline_result["raw_extractions"]["analyze"] = analysis
            pipeline_result["stages_completed"].append("analyze")
            
            # ========== 阶段 3: 搜索补充 ==========
            enriched = await self._stage_search(extraction, analysis)
            pipeline_result["raw_extractions"]["search"] = enriched
            pipeline_result["stages_completed"].append("search")
            
            # ========== 阶段 4: 验证 ==========
            verification = await self._stage_verify(extraction, analysis, enriched)
            pipeline_result["raw_extractions"]["verify"] = verification
            pipeline_result["stages_completed"].append("verify")
            
            confidence = verification.get("confidence", 0.5)
            
            # ========== 阶段 5: 归纳总结 ==========
            final = await self._stage_synthesize(extraction, analysis, enriched, verification)
            pipeline_result["final_result"] = final
            pipeline_result["stages_completed"].append("synthesize")
            
            # 添加验证标签
            if confidence >= 0.7:
                tags = final.get("tags", [])
                if "已验证" not in tags:
                    tags.append("已验证")
                final["tags"] = tags
            
            await self._notify(f"🎉 #{kid} | 深度分析完成!\n📝 {final.get('title', '')[:50]}")
            
            return final
            
        except Exception as e:
            error_msg = str(e)
            pipeline_result["errors"].append(error_msg)
            logger.error(f"Pipeline failed: {e}")
            await self._notify(f"⚠️ #{kid} | 管道异常，使用基础结果")
            
            # 返回提取阶段的基础结果
            ext = pipeline_result["raw_extractions"].get("extract", {})
            return {
                "title": ext.get("title", "未知内容"),
                "summary": ext.get("raw_summary", content[:500] if content else "图片内容"),
                "key_points": ext.get("detected_features", []),
                "tags": ext.get("detected_names", []),
                "category": "未分类",
                "difficulty": "中级",
                "action_items": [],
                "repo_url": (ext.get("detected_urls", []) or [None])[0]
            }
    
    async def _simple_distill(self, content: str, images: Optional[List[str]], kid: int) -> Dict[str, Any]:
        """
        简化版单次蒸馏 - 更可靠
        """
        # 处理图片
        actual_content = content
        if images and len(images) > 0:
            image_text = await ai_service.analyze_image(
                images, 
                context="请详细描述图片中的所有内容。如果是GitHub页面，提取仓库名、描述、star数、技术栈等。如果是代码，说明代码功能。"
            )
            if image_text:
                actual_content = f"{image_text}\n\n{content}" if content else image_text
        
        if not actual_content or len(actual_content.strip()) < 10:
            return {"error": "没有有效内容"}
        
        prompt = """你是知识管理专家。请分析以下内容并生成知识卡片。

输出 JSON 格式：
{
    "title": "简洁的标题",
    "summary": "150-250字的完整摘要，包含：是什么、核心功能、适用场景",
    "key_points": ["关键点1", "关键点2", "关键点3", "关键点4", "关键点5"],
    "tags": ["标签1", "标签2", "标签3"],
    "category": "分类（技术/工具/教程/概念）",
    "difficulty": "难度（入门/中级/高级）",
    "action_items": ["可执行的行动1", "行动2"],
    "usage_example": "使用示例代码或命令（如适用）",
    "deployment_guide": "部署步骤（如果是项目）",
    "is_open_source": true/false,
    "repo_url": "GitHub地址（如有）"
}

要求：
1. 如果是 GitHub 项目，必须提取仓库地址
2. 提供实用的使用示例
3. 标签要精准
4. 摘要要全面"""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"请分析以下内容：\n\n{actual_content[:4000]}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.3)
        
        if not result:
            return {"error": "AI 未返回结果"}
        
        try:
            return self._parse_json(result)
        except Exception as e:
            logger.error(f"Simple distill parse error: {e}")
            # 尝试从响应中提取有用信息
            return {
                "title": actual_content[:80],
                "summary": actual_content[:300],
                "key_points": [],
                "tags": [],
                "category": "未分类",
                "difficulty": "中级",
                "action_items": [],
                "error": f"解析失败: {str(e)}"
            }
    
    async def _stage_extract(self, content: str, images: Optional[List[str]]) -> Dict[str, Any]:
        """
        阶段1: 提取
        从原始内容和图片中提取基础信息
        """
        prompt = """你是一个信息提取专家。你的任务是从给定内容中提取所有关键信息。

请仔细分析内容，提取以下信息（JSON格式）：

{
    "title": "内容的核心主题/标题",
    "raw_summary": "内容的原始摘要（保持客观，不添加解释）",
    "detected_urls": ["从内容中发现的所有URL链接"],
    "detected_names": ["发现的项目名/产品名/技术名"],
    "detected_versions": ["发现的版本号"],
    "detected_commands": ["发现的命令行/代码片段"],
    "detected_features": ["发现的功能特性列表"],
    "content_language": "内容语言（中文/英文/混合）",
    "has_code": true/false,
    "has_diagram": true/false,
    "source_hints": ["可能的来源提示，如GitHub/文档/教程等"]
}

提取要求：
1. 保持信息的原始性，不要添加你的理解
2. URL要完整提取，包括GitHub链接、文档链接等
3. 如果是开源项目，特别注意提取仓库地址
4. 提取所有版本号、日期等关键数据
5. 代码片段原样提取"""

        # 处理图片
        actual_content = content
        if images and len(images) > 0:
            image_text = await ai_service.analyze_image(
                images, 
                context="请详细描述图片中的所有文字、代码、链接、图表内容。如果是GitHub页面，请提取仓库名、star数、描述等所有可见信息。"
            )
            if image_text:
                actual_content = f"[图片内容]\n{image_text}\n\n[文字内容]\n{content}" if content else f"[图片内容]\n{image_text}"
        
        if not actual_content or len(actual_content.strip()) < 10:
            return {"error": "没有有效内容可提取"}
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"请提取以下内容的信息：\n\n{actual_content}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.2)
        
        try:
            return self._parse_json(result)
        except:
            return {
                "title": actual_content[:100],
                "raw_summary": actual_content[:500],
                "detected_urls": self._extract_urls(actual_content),
                "detected_names": [],
                "content_language": "未知"
            }
    
    async def _stage_analyze(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """
        阶段2: 分析
        深度理解内容的结构、技术细节和应用场景
        """
        prompt = """你是一个资深技术架构师和数据分析师。基于提取的信息，进行深度分析。

请分析并输出（JSON格式）：

{
    "content_type": "内容类型（开源项目/技术教程/工具介绍/概念解释/新闻资讯/其他）",
    "domain": "所属领域（Web开发/区块链/AI/DevOps/数据库/其他）",
    "tech_stack": ["涉及的技术栈"],
    "architecture_pattern": "架构模式（如有）",
    "complexity_level": "复杂度（入门/中级/高级/专家）",
    "target_audience": "目标受众",
    "prerequisites": ["前置知识要求"],
    "use_cases": ["适用场景"],
    "advantages": ["优点/亮点"],
    "limitations": ["局限性/注意事项"],
    "related_technologies": ["相关技术/竞品"],
    "learning_path": "建议学习路径",
    "estimated_learning_time": "预估学习时间"
}

分析要求：
1. 站在技术架构师角度，分析技术深度
2. 识别核心价值和差异化特点
3. 分析适用场景和局限性
4. 提供实用的学习建议"""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"请分析以下提取的信息：\n\n{json.dumps(extraction, ensure_ascii=False, indent=2)}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.3)
        
        try:
            return self._parse_json(result)
        except:
            return {
                "content_type": "未知",
                "domain": "未知",
                "tech_stack": [],
                "complexity_level": "中级"
            }
    
    async def _stage_search(self, extraction: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        阶段3: 搜索补充
        基于提取的信息，搜索补充上下文
        """
        prompt = """你是一个知识搜索专家。基于已知信息，推断和补充可能的相关信息。

你需要：
1. 如果发现了项目名但没有URL，推断可能的GitHub/官网地址
2. 补充常见的安装方式和使用命令
3. 推断相关的文档、教程资源
4. 识别相关的生态系统工具

请输出（JSON格式）：

{
    "inferred_github_url": "推断的GitHub地址（如果是开源项目）",
    "inferred_docs_url": "推断的文档地址",
    "inferred_website": "推断的官网地址",
    "found_urls": ["所有已知和推断的URL列表"],
    "install_commands": {
        "npm": "npm install xxx",
        "pip": "pip install xxx",
        "docker": "docker pull xxx",
        "other": "其他安装方式"
    },
    "quick_start": "快速开始步骤",
    "related_resources": [
        {"name": "资源名", "url": "资源URL", "type": "文档/教程/视频"}
    ],
    "ecosystem_tools": ["生态系统相关工具"],
    "community": {
        "discord": "Discord链接",
        "twitter": "Twitter链接",
        "forum": "论坛链接"
    }
}

注意：
1. 只推断你有把握的信息
2. GitHub项目通常格式为 https://github.com/owner/repo
3. npm包通常有 npmjs.com 页面
4. 主流项目通常有官方文档站点"""

        context = {
            "title": extraction.get("title"),
            "names": extraction.get("detected_names", []),
            "urls": extraction.get("detected_urls", []),
            "tech_stack": analysis.get("tech_stack", []),
            "domain": analysis.get("domain")
        }
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"基于以下信息进行搜索补充：\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.4)
        
        try:
            return self._parse_json(result)
        except:
            return {
                "found_urls": extraction.get("detected_urls", []),
                "install_commands": {},
                "quick_start": ""
            }
    
    async def _stage_verify(
        self, 
        extraction: Dict[str, Any], 
        analysis: Dict[str, Any],
        enriched: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        阶段4: 验证
        交叉验证关键信息的准确性
        """
        prompt = """你是一个严谨的信息验证专家。请验证以下信息的准确性和一致性。

验证要点：
1. URL格式是否正确
2. 技术栈信息是否匹配
3. 版本号是否合理
4. 命令语法是否正确
5. 信息是否自洽

请输出（JSON格式）：

{
    "confidence": 0.0-1.0,
    "verified_items": [
        {"item": "xxx", "status": "verified/unverified/uncertain", "note": "备注"}
    ],
    "corrections": [
        {"original": "原始信息", "corrected": "修正后", "reason": "修正原因"}
    ],
    "warnings": ["需要注意的问题"],
    "missing_critical_info": ["缺失的关键信息"],
    "data_quality_score": 0-100,
    "recommendation": "信息质量评价和建议"
}

验证标准：
- verified: 信息确定正确
- unverified: 无法验证
- uncertain: 信息可能有误"""

        all_info = {
            "extraction": extraction,
            "analysis": analysis,
            "enriched": enriched
        }
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"请验证以下信息：\n\n{json.dumps(all_info, ensure_ascii=False, indent=2)}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.2)
        
        try:
            return self._parse_json(result)
        except:
            return {
                "confidence": 0.5,
                "verified_items": [],
                "corrections": [],
                "warnings": ["验证过程出现异常"]
            }
    
    async def _stage_synthesize(
        self,
        extraction: Dict[str, Any],
        analysis: Dict[str, Any],
        enriched: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        阶段5: 归纳总结
        综合所有信息，生成最终的知识卡片
        """
        prompt = """你是一个知识管理专家。请综合所有阶段的分析结果，生成一个全面、准确、实用的知识卡片。

知识卡片要求：
1. 标题：简洁明了，突出核心价值
2. 摘要：200字左右，涵盖是什么、能做什么、为什么重要
3. 关键点：5-8个，具体可操作
4. 标签：精准的技术标签，便于搜索
5. 使用示例：实际可运行的代码/命令
6. 部署指南：如果是项目，提供部署步骤

请输出（JSON格式）：

{
    "title": "知识标题",
    "summary": "全面的摘要（包含核心价值、适用场景、技术特点）",
    "key_points": [
        "关键点1（具体、可操作）",
        "关键点2",
        "关键点3"
    ],
    "tags": ["标签1", "标签2"],
    "category": "分类（技术/工具/概念/教程）",
    "difficulty": "难度（入门/中级/高级）",
    "action_items": [
        "可执行的下一步行动1",
        "行动2"
    ],
    "usage_example": "```language\\n完整的使用示例代码\\n```",
    "deployment_guide": "部署步骤（如适用）：\\n1. 步骤1\\n2. 步骤2",
    "is_open_source": true/false,
    "repo_url": "GitHub仓库地址（如有）",
    "official_docs": "官方文档地址",
    "quick_reference": {
        "install": "安装命令",
        "run": "运行命令",
        "docs": "文档链接"
    },
    "related_topics": ["相关主题1", "相关主题2"],
    "learning_resources": [
        {"name": "资源名", "url": "链接", "type": "类型"}
    ],
    "pros_cons": {
        "pros": ["优点1", "优点2"],
        "cons": ["局限1", "局限2"]
    },
    "best_practices": ["最佳实践1", "最佳实践2"],
    "common_mistakes": ["常见错误1", "常见错误2"]
}

生成要求：
1. 信息必须基于前面阶段的分析，不要编造
2. 使用示例必须是可运行的
3. 如果是GitHub项目，必须包含仓库地址
4. 标签要精准，便于后续搜索
5. 考虑实际使用场景，提供实用建议"""

        all_info = {
            "extraction": extraction,
            "analysis": analysis,
            "enriched": enriched,
            "verification": verification
        }
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"请基于以下所有阶段的分析结果，生成知识卡片：\n\n{json.dumps(all_info, ensure_ascii=False, indent=2)}"}
        ]
        
        result = await ai_service._call_api(messages, temperature=0.4)
        
        try:
            parsed = self._parse_json(result)
            
            # 确保必要字段存在
            return {
                "title": parsed.get("title", extraction.get("title", "未知")),
                "summary": parsed.get("summary", extraction.get("raw_summary", "")),
                "key_points": parsed.get("key_points", []),
                "tags": parsed.get("tags", []),
                "category": parsed.get("category", analysis.get("domain", "未分类")),
                "difficulty": parsed.get("difficulty", analysis.get("complexity_level", "中级")),
                "action_items": parsed.get("action_items", []),
                "usage_example": parsed.get("usage_example"),
                "deployment_guide": parsed.get("deployment_guide"),
                "is_open_source": parsed.get("is_open_source", False),
                "repo_url": parsed.get("repo_url") or enriched.get("inferred_github_url"),
                "official_docs": parsed.get("official_docs"),
                "quick_reference": parsed.get("quick_reference"),
                "related_topics": parsed.get("related_topics", []),
                "learning_resources": parsed.get("learning_resources", []),
                "pros_cons": parsed.get("pros_cons"),
                "best_practices": parsed.get("best_practices", []),
                "common_mistakes": parsed.get("common_mistakes", [])
            }
        except Exception as e:
            logger.error(f"Synthesize parsing error: {e}")
            return {
                "title": extraction.get("title", "处理失败"),
                "summary": extraction.get("raw_summary", ""),
                "key_points": [],
                "tags": analysis.get("tech_stack", []),
                "category": analysis.get("domain", "未分类"),
                "difficulty": analysis.get("complexity_level", "中级"),
                "action_items": []
            }
    
    def _parse_json(self, text: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
        if not text:
            return {}
        
        # 清理 markdown 代码块
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return json.loads(cleaned.strip())
    
    def _extract_urls(self, text: str) -> List[str]:
        """从文本中提取 URL"""
        url_pattern = r'https?://[^\s<>"\')\]]*'
        urls = re.findall(url_pattern, text)
        return list(set(urls))


# 全局实例
distillation_pipeline = DistillationPipeline()

