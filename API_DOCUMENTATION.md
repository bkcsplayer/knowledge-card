# Knowledge Distillery API 文档

> 🧪 AI 驱动的知识管理系统 API 接口文档
> 
> Base URL: `http://YOUR_SERVER_IP:8000`

---

## 📋 目录

1. [快速开始](#快速开始)
2. [认证说明](#认证说明)
3. [知识管理 API](#知识管理-api)
4. [AI 蒸馏 API](#ai-蒸馏-api)
5. [搜索 API](#搜索-api)
6. [学习路线 API](#学习路线-api)
7. [文件上传 API](#文件上传-api)
8. [报告 API](#报告-api)
9. [错误处理](#错误处理)
10. [代码示例](#代码示例)

---

## 快速开始

### 基础请求示例

```bash
# 健康检查
curl http://YOUR_SERVER:8000/

# 获取知识列表
curl http://YOUR_SERVER:8000/api/v1/knowledge/

# 添加知识（AI 自动蒸馏）
curl -X POST http://YOUR_SERVER:8000/api/v1/knowledge/ \
  -H "Content-Type: application/json" \
  -d '{"content": "你的知识内容...", "auto_process": true}'
```

### 响应格式

所有 API 返回 JSON 格式数据：

```json
{
  "id": 1,
  "title": "知识标题",
  "summary": "AI 生成的摘要",
  "key_points": ["关键点1", "关键点2"],
  "tags": ["标签1", "标签2"],
  ...
}
```

---

## 认证说明

当前版本 API 无需认证，适合内部使用。如需添加认证，请联系管理员。

---

## 知识管理 API

### 1. 获取知识列表

```
GET /api/v1/knowledge/
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| skip | int | 否 | 跳过条数，默认 0 |
| limit | int | 否 | 返回条数，默认 50，最大 100 |
| category | string | 否 | 按分类过滤 |
| tag | string | 否 | 按标签过滤 |
| search | string | 否 | 搜索关键词 |
| include_archived | bool | 否 | 是否包含已归档，默认 false |

**请求示例：**

```bash
# 获取技术分类的知识
curl "http://YOUR_SERVER:8000/api/v1/knowledge/?category=技术&limit=10"

# 搜索关键词
curl "http://YOUR_SERVER:8000/api/v1/knowledge/?search=React"
```

**响应示例：**

```json
[
  {
    "id": 1,
    "title": "React Hooks 基础概念",
    "original_content": "原始内容...",
    "summary": "React Hooks 是 React 16.8 引入的新特性...",
    "key_points": [
      "useState 用于状态管理",
      "useEffect 用于副作用处理"
    ],
    "tags": ["React", "Hooks", "前端"],
    "category": "技术",
    "difficulty": "中等",
    "action_items": ["学习 useState", "实践 useEffect"],
    "usage_example": "const [count, setCount] = useState(0)",
    "deployment_guide": null,
    "is_open_source": false,
    "repo_url": null,
    "images": [],
    "processing_status": "completed",
    "processing_steps": [...],
    "is_processed": true,
    "is_archived": false,
    "created_at": "2024-12-10T12:00:00",
    "updated_at": "2024-12-10T12:01:00",
    "processed_at": "2024-12-10T12:01:00"
  }
]
```

---

### 2. 创建知识（AI 自动蒸馏）

```
POST /api/v1/knowledge/
```

**请求体：**

```json
{
  "content": "你要存储和蒸馏的内容",
  "title": "可选的标题",
  "source_type": "manual",
  "source_url": "可选的来源 URL",
  "images": ["图片URL1", "图片URL2"],
  "auto_process": true
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | ✅ | 知识内容 |
| title | string | 否 | 标题（不填则 AI 生成） |
| source_type | string | 否 | 来源类型：manual/url/file/api |
| source_url | string | 否 | 来源 URL |
| images | array | 否 | 图片 URL 列表 |
| auto_process | bool | 否 | 是否 AI 蒸馏，默认 true |

**请求示例：**

```bash
curl -X POST http://YOUR_SERVER:8000/api/v1/knowledge/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Docker 是一个开源的容器化平台，它允许开发者将应用程序及其依赖打包到一个轻量级、可移植的容器中。",
    "auto_process": true
  }'
```

**响应示例：**

```json
{
  "id": 5,
  "title": "Docker 容器化技术基础",
  "summary": "Docker 是一个开源容器化平台，通过将应用及其依赖打包成轻量级容器...",
  "key_points": [
    "Docker 是开源的容器化平台",
    "可将应用和依赖打包成轻量级容器",
    "确保开发、测试和生产环境的一致性"
  ],
  "tags": ["Docker", "容器化", "DevOps"],
  "category": "技术",
  "difficulty": "中等",
  "action_items": [
    "安装 Docker 并学习基本命令",
    "尝试将一个简单应用容器化"
  ],
  "usage_example": "docker run -d -p 80:80 nginx",
  "processing_status": "completed",
  "is_processed": true,
  ...
}
```

---

### 3. 获取单条知识

```
GET /api/v1/knowledge/{knowledge_id}
```

**请求示例：**

```bash
curl http://YOUR_SERVER:8000/api/v1/knowledge/1
```

---

### 4. 更新知识

```
PUT /api/v1/knowledge/{knowledge_id}
```

**请求体：**

```json
{
  "title": "新标题",
  "summary": "新摘要",
  "tags": ["新标签1", "新标签2"],
  "category": "新分类"
}
```

---

### 5. 删除知识

```
DELETE /api/v1/knowledge/{knowledge_id}
```

---

### 6. 归档知识（软删除）

```
POST /api/v1/knowledge/{knowledge_id}/archive
```

---

### 7. 重新 AI 处理

```
POST /api/v1/knowledge/{knowledge_id}/reprocess
```

---

### 8. 获取统计数据

```
GET /api/v1/knowledge/stats
```

**响应示例：**

```json
{
  "total": 42,
  "recent_7_days": 5,
  "processed": 40,
  "unprocessed": 2,
  "categories": {
    "技术": 25,
    "商业": 10,
    "生活": 7
  }
}
```

---

## AI 蒸馏 API

### 1. 直接蒸馏内容（不存储）

```
POST /api/v1/ai/distill
```

**请求体：**

```json
{
  "content": "要蒸馏的内容",
  "context": "可选的上下文说明"
}
```

**响应示例：**

```json
{
  "title": "生成的标题",
  "summary": "100-200字的摘要",
  "key_points": ["关键点1", "关键点2", "关键点3"],
  "tags": ["标签1", "标签2"],
  "category": "分类",
  "difficulty": "中等",
  "action_items": ["行动建议1", "行动建议2"],
  "usage_example": "使用示例代码",
  "deployment_guide": "部署指南（如果是开源项目）",
  "is_open_source": false,
  "repo_url": null
}
```

---

### 2. AI 问答

```
POST /api/v1/ai/ask
```

**请求体：**

```json
{
  "question": "React Hooks 是什么？",
  "context": "可选的知识库上下文"
}
```

**响应示例：**

```json
{
  "question": "React Hooks 是什么？",
  "answer": "React Hooks 是 React 16.8 引入的新特性...",
  "has_context": false
}
```

---

### 3. 检查 AI 状态

```
GET /api/v1/ai/status
```

**响应示例：**

```json
{
  "configured": true,
  "model": "anthropic/claude-3.5-sonnet",
  "base_url": "https://openrouter.ai/api/v1"
}
```

---

## 搜索 API

### 1. 语义搜索（带 AI 回答）

```
POST /api/v1/search/
```

**请求体：**

```json
{
  "query": "如何优化 React 性能？",
  "limit": 10,
  "include_answer": true
}
```

**响应示例：**

```json
{
  "query": "如何优化 React 性能？",
  "results": [
    {
      "id": 3,
      "title": "React 性能优化技巧",
      "summary": "...",
      "category": "技术",
      "tags": ["React", "性能"],
      "similarity": 0.89,
      "snippet": "React 性能优化的关键在于..."
    }
  ],
  "answer": "根据知识库内容，React 性能优化可以从以下几个方面入手...",
  "total": 5
}
```

---

### 2. 查找相似知识

```
GET /api/v1/search/similar/{knowledge_id}?limit=5
```

**响应示例：**

```json
{
  "source_id": 1,
  "source_title": "React Hooks",
  "similar": [
    {
      "id": 3,
      "title": "React 状态管理",
      "summary": "...",
      "category": "技术",
      "tags": ["React", "状态管理"],
      "similarity": 0.85
    }
  ]
}
```

---

## 学习路线 API

### 1. 生成学习路线

```
POST /api/v1/learning/generate
```

**请求体：**

```json
{
  "topic": "React",
  "level": "beginner"
}
```

**level 可选值：** `beginner`, `intermediate`, `advanced`

**响应示例：**

```json
{
  "topic": "React",
  "level": "beginner",
  "total_duration": "4-6 周",
  "prerequisites": ["HTML/CSS 基础", "JavaScript ES6+"],
  "goals": [
    "理解 React 核心概念",
    "能够构建简单的 React 应用",
    "掌握组件化开发思想"
  ],
  "steps": [
    {
      "order": 1,
      "title": "React 基础概念",
      "description": "学习 JSX、组件、Props 等基础知识",
      "duration": "1 周",
      "knowledge_ids": [1, 3],
      "resources": ["官方文档", "知识库相关内容"]
    },
    {
      "order": 2,
      "title": "React Hooks",
      "description": "学习 useState、useEffect 等常用 Hooks",
      "duration": "1-2 周",
      "knowledge_ids": [2],
      "resources": ["实践项目练习"]
    }
  ]
}
```

---

### 2. 获取可用学习主题

```
GET /api/v1/learning/topics
```

**响应示例：**

```json
{
  "categories": ["技术", "商业", "生活"],
  "popular_tags": ["React", "Python", "Docker", "AI"],
  "suggested_topics": ["技术", "React", "Python", "Docker"]
}
```

---

## 文件上传 API

### 1. 上传单张图片

```
POST /api/v1/upload/image
```

**请求：** `multipart/form-data`

```bash
curl -X POST http://YOUR_SERVER:8000/api/v1/upload/image \
  -F "file=@/path/to/image.jpg"
```

**响应示例：**

```json
{
  "status": "success",
  "filename": "abc123.jpg",
  "url": "/api/v1/upload/images/abc123.jpg",
  "size": 102400,
  "content_type": "image/jpeg",
  "uploaded_at": "2024-12-10T12:00:00"
}
```

---

### 2. 批量上传图片

```
POST /api/v1/upload/images/batch
```

```bash
curl -X POST http://YOUR_SERVER:8000/api/v1/upload/images/batch \
  -F "files=@image1.jpg" \
  -F "files=@image2.png"
```

---

### 3. 获取图片

```
GET /api/v1/upload/images/{filename}
```

---

### 4. 列出所有图片

```
GET /api/v1/upload/list/images
```

---

## 报告 API

### 1. 发送测试邮件

```
POST /api/v1/reports/test-email
```

---

### 2. 发送每日报告

```
POST /api/v1/reports/send/daily
```

---

### 3. 预览每日报告

```
GET /api/v1/reports/preview/daily
```

---

### 4. 查看定时任务状态

```
GET /api/v1/reports/schedule
```

---

## 错误处理

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（如 AI 未配置） |

---

## 代码示例

### Python

```python
import requests

BASE_URL = "http://YOUR_SERVER:8000"

# 获取知识列表
response = requests.get(f"{BASE_URL}/api/v1/knowledge/")
knowledge_list = response.json()
print(f"共有 {len(knowledge_list)} 条知识")

# 添加新知识
new_knowledge = requests.post(
    f"{BASE_URL}/api/v1/knowledge/",
    json={
        "content": "Python 是一种高级编程语言，以简洁易读著称。",
        "auto_process": True
    }
)
result = new_knowledge.json()
print(f"创建成功: {result['title']}")

# 语义搜索
search_result = requests.post(
    f"{BASE_URL}/api/v1/search/",
    json={
        "query": "如何学习编程？",
        "limit": 5,
        "include_answer": True
    }
)
data = search_result.json()
print(f"AI 回答: {data['answer']}")
```

### JavaScript / Node.js

```javascript
const BASE_URL = 'http://YOUR_SERVER:8000';

// 获取知识列表
async function getKnowledgeList() {
  const response = await fetch(`${BASE_URL}/api/v1/knowledge/`);
  const data = await response.json();
  console.log(`共有 ${data.length} 条知识`);
  return data;
}

// 添加新知识
async function addKnowledge(content) {
  const response = await fetch(`${BASE_URL}/api/v1/knowledge/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: content,
      auto_process: true
    })
  });
  const result = await response.json();
  console.log(`创建成功: ${result.title}`);
  return result;
}

// 语义搜索
async function semanticSearch(query) {
  const response = await fetch(`${BASE_URL}/api/v1/search/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      limit: 5,
      include_answer: true
    })
  });
  const data = await response.json();
  console.log(`AI 回答: ${data.answer}`);
  return data;
}

// 使用示例
getKnowledgeList();
addKnowledge('Vue.js 是一个渐进式 JavaScript 框架');
semanticSearch('什么是前端框架？');
```

### cURL

```bash
# 获取所有知识
curl -s http://YOUR_SERVER:8000/api/v1/knowledge/ | jq

# 添加知识
curl -X POST http://YOUR_SERVER:8000/api/v1/knowledge/ \
  -H "Content-Type: application/json" \
  -d '{"content": "学习内容...", "auto_process": true}' | jq

# 搜索
curl -X POST http://YOUR_SERVER:8000/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "如何学习?", "include_answer": true}' | jq

# 生成学习路线
curl -X POST http://YOUR_SERVER:8000/api/v1/learning/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python", "level": "beginner"}' | jq
```

---

## 📚 Swagger 文档

访问交互式 API 文档：

- **Swagger UI:** `http://YOUR_SERVER:8000/docs`
- **ReDoc:** `http://YOUR_SERVER:8000/redoc`

---

## 🔗 相关链接

- 项目主页: `http://YOUR_SERVER:5173`
- 健康检查: `http://YOUR_SERVER:8000/health`

---

## 📝 更新日志

### v0.2.0 (2024-12-10)
- ✨ 丰富知识卡片 UI
- 🔗 知识点自动关联
- 📊 知识图谱可视化
- 🛤️ 学习路线生成
- 📷 图片上传功能
- 📧 邮件报告系统

### v0.1.0 (2024-12-10)
- 🎉 初始版本
- 🧪 AI 知识蒸馏
- 🔍 语义搜索
- 📚 知识库 CRUD

---

> 💡 **提示：** 将 `YOUR_SERVER` 替换为实际服务器 IP 地址（如 `74.48.192.171`）

