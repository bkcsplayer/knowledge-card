"""
URL Content Fetching Service
抓取 URL 内容，特别优化 GitHub 项目处理

支持：
1. GitHub 仓库 - 使用 GitHub API 获取完整信息
2. 普通网页 - 抓取 HTML 并提取主要内容
3. 其他 URL - 基础处理
"""

import re
import logging
import aiohttp
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLService:
    """URL 内容抓取服务"""
    
    def __init__(self):
        self.github_api = "https://api.github.com"
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            "User-Agent": "Knowledge-Distillery/1.0",
            "Accept": "application/json"
        }
    
    def is_github_url(self, url: str) -> bool:
        """检测是否是 GitHub URL"""
        return "github.com" in url.lower()
    
    def parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        解析 GitHub URL，提取 owner 和 repo
        
        支持格式：
        - https://github.com/owner/repo
        - https://github.com/owner/repo/xxx
        - github.com/owner/repo
        """
        patterns = [
            r'github\.com[/:]([^/]+)/([^/\s?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2).replace('.git', '')
                return {"owner": owner, "repo": repo}
        
        return None
    
    async def fetch_github_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        通过 GitHub API 获取仓库详细信息
        """
        result = {
            "type": "github_repo",
            "owner": owner,
            "repo": repo,
            "url": f"https://github.com/{owner}/{repo}",
            "success": False
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 获取仓库基本信息
                repo_url = f"{self.github_api}/repos/{owner}/{repo}"
                async with session.get(repo_url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result.update({
                            "success": True,
                            "name": data.get("name"),
                            "full_name": data.get("full_name"),
                            "description": data.get("description") or "无描述",
                            "homepage": data.get("homepage"),
                            "stars": data.get("stargazers_count", 0),
                            "forks": data.get("forks_count", 0),
                            "watchers": data.get("watchers_count", 0),
                            "open_issues": data.get("open_issues_count", 0),
                            "language": data.get("language"),
                            "topics": data.get("topics", []),
                            "license": data.get("license", {}).get("name") if data.get("license") else None,
                            "default_branch": data.get("default_branch", "main"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "pushed_at": data.get("pushed_at"),
                            "is_fork": data.get("fork", False),
                            "is_archived": data.get("archived", False),
                            "html_url": data.get("html_url"),
                            "clone_url": data.get("clone_url"),
                            "size_kb": data.get("size", 0)
                        })
                    else:
                        logger.warning(f"GitHub API returned {resp.status} for {owner}/{repo}")
                        result["error"] = f"GitHub API 返回 {resp.status}"
                
                # 获取 README 内容
                if result["success"]:
                    readme_url = f"{self.github_api}/repos/{owner}/{repo}/readme"
                    async with session.get(readme_url, headers={**self.headers, "Accept": "application/vnd.github.raw"}) as resp:
                        if resp.status == 200:
                            readme_content = await resp.text()
                            # 限制 README 长度
                            result["readme"] = readme_content[:8000] if len(readme_content) > 8000 else readme_content
                            result["readme_truncated"] = len(readme_content) > 8000
                        else:
                            result["readme"] = None
                
                # 获取语言统计
                if result["success"]:
                    langs_url = f"{self.github_api}/repos/{owner}/{repo}/languages"
                    async with session.get(langs_url, headers=self.headers) as resp:
                        if resp.status == 200:
                            result["languages"] = await resp.json()
                
                # 获取最近 releases
                if result["success"]:
                    releases_url = f"{self.github_api}/repos/{owner}/{repo}/releases?per_page=3"
                    async with session.get(releases_url, headers=self.headers) as resp:
                        if resp.status == 200:
                            releases = await resp.json()
                            result["releases"] = [
                                {
                                    "tag": r.get("tag_name"),
                                    "name": r.get("name"),
                                    "published_at": r.get("published_at"),
                                    "prerelease": r.get("prerelease")
                                }
                                for r in releases[:3]
                            ]
                
        except aiohttp.ClientError as e:
            logger.error(f"GitHub API request failed: {e}")
            result["error"] = f"网络请求失败: {str(e)}"
        except Exception as e:
            logger.error(f"GitHub fetch error: {e}")
            result["error"] = f"处理失败: {str(e)}"
        
        return result
    
    async def fetch_webpage(self, url: str) -> Dict[str, Any]:
        """
        抓取普通网页内容
        """
        result = {
            "type": "webpage",
            "url": url,
            "success": False
        }
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml"
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        
                        # 提取标题
                        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                        title = title_match.group(1).strip() if title_match else None
                        
                        # 提取 meta description
                        desc_match = re.search(
                            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                            html, re.IGNORECASE
                        )
                        description = desc_match.group(1).strip() if desc_match else None
                        
                        # 提取正文（简单处理：移除脚本和样式，提取文本）
                        # 移除 script 和 style
                        clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
                        # 移除 HTML 标签
                        clean = re.sub(r'<[^>]+>', ' ', clean)
                        # 清理空白
                        clean = re.sub(r'\s+', ' ', clean).strip()
                        
                        # 截取正文
                        body_text = clean[:5000] if len(clean) > 5000 else clean
                        
                        result.update({
                            "success": True,
                            "title": title,
                            "description": description,
                            "content": body_text,
                            "content_length": len(clean),
                            "truncated": len(clean) > 5000
                        })
                    else:
                        result["error"] = f"HTTP {resp.status}"
                        
        except aiohttp.ClientError as e:
            logger.error(f"Webpage fetch failed: {e}")
            result["error"] = f"网络请求失败: {str(e)}"
        except Exception as e:
            logger.error(f"Webpage fetch error: {e}")
            result["error"] = f"处理失败: {str(e)}"
        
        return result
    
    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        自动检测 URL 类型并获取内容
        
        返回格式：
        {
            "type": "github_repo" | "webpage" | "unknown",
            "url": "原始 URL",
            "success": bool,
            "error": "错误信息（如有）",
            ... 其他字段取决于类型
        }
        """
        if not url or not url.strip():
            return {"type": "unknown", "url": "", "success": False, "error": "URL 为空"}
        
        url = url.strip()
        
        # 确保有协议
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # GitHub 仓库
        if self.is_github_url(url):
            parsed = self.parse_github_url(url)
            if parsed:
                logger.info(f"Fetching GitHub repo: {parsed['owner']}/{parsed['repo']}")
                return await self.fetch_github_repo(parsed["owner"], parsed["repo"])
        
        # 普通网页
        logger.info(f"Fetching webpage: {url}")
        return await self.fetch_webpage(url)
    
    def format_github_for_distillation(self, data: Dict[str, Any]) -> str:
        """
        将 GitHub 数据格式化为供 AI 分析的文本
        """
        if not data.get("success"):
            return f"无法获取 GitHub 仓库信息: {data.get('error', '未知错误')}"
        
        lines = [
            f"# GitHub 项目: {data.get('full_name')}",
            "",
            f"**仓库地址**: {data.get('html_url')}",
            f"**描述**: {data.get('description')}",
            "",
            "## 项目统计",
            f"- ⭐ Stars: {data.get('stars', 0):,}",
            f"- 🔱 Forks: {data.get('forks', 0):,}",
            f"- 👁️ Watchers: {data.get('watchers', 0):,}",
            f"- 📋 Issues: {data.get('open_issues', 0)}",
            f"- 💾 大小: {data.get('size_kb', 0):,} KB",
            "",
            f"**主要语言**: {data.get('language') or '未知'}",
            f"**许可证**: {data.get('license') or '未指定'}",
            f"**创建时间**: {data.get('created_at', '')[:10] if data.get('created_at') else '未知'}",
            f"**最后更新**: {data.get('pushed_at', '')[:10] if data.get('pushed_at') else '未知'}",
        ]
        
        # Topics
        if data.get("topics"):
            lines.append("")
            lines.append(f"**标签**: {', '.join(data['topics'])}")
        
        # 语言统计
        if data.get("languages"):
            lines.append("")
            lines.append("## 语言占比")
            total = sum(data["languages"].values())
            for lang, bytes_count in sorted(data["languages"].items(), key=lambda x: -x[1])[:5]:
                pct = (bytes_count / total * 100) if total > 0 else 0
                lines.append(f"- {lang}: {pct:.1f}%")
        
        # Releases
        if data.get("releases"):
            lines.append("")
            lines.append("## 最新版本")
            for rel in data["releases"]:
                tag = rel.get("tag") or "无标签"
                name = rel.get("name") or tag
                date = rel.get("published_at", "")[:10] if rel.get("published_at") else ""
                lines.append(f"- {name} ({date})")
        
        # Homepage
        if data.get("homepage"):
            lines.append("")
            lines.append(f"**官方网站**: {data['homepage']}")
        
        # Clone URL
        lines.append("")
        lines.append("## 安装使用")
        lines.append(f"```bash")
        lines.append(f"git clone {data.get('clone_url')}")
        lines.append(f"cd {data.get('repo')}")
        lines.append(f"```")
        
        # README 摘要
        if data.get("readme"):
            lines.append("")
            lines.append("## README 内容")
            readme_preview = data["readme"][:3000]
            if len(data["readme"]) > 3000:
                readme_preview += "\n\n[... README 内容已截断 ...]"
            lines.append(readme_preview)
        
        return "\n".join(lines)
    
    def format_webpage_for_distillation(self, data: Dict[str, Any]) -> str:
        """
        将网页数据格式化为供 AI 分析的文本
        """
        if not data.get("success"):
            return f"无法获取网页内容: {data.get('error', '未知错误')}"
        
        lines = [
            f"# 网页: {data.get('title') or '无标题'}",
            "",
            f"**URL**: {data.get('url')}",
        ]
        
        if data.get("description"):
            lines.append(f"**描述**: {data['description']}")
        
        lines.append("")
        lines.append("## 页面内容")
        lines.append(data.get("content", "无内容"))
        
        return "\n".join(lines)


# 全局实例
url_service = URLService()

