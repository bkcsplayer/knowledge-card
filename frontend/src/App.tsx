import { useState, useEffect, useRef } from 'react'
import './App.css'

// 动态获取后端 API 地址
const API_BASE = `http://${window.location.hostname}:8000`

// 认证配置
const AUTH_CONFIG = {
  username: 'admin',
  password: '1q2w3e4R.'
}

interface ProcessingStep {
  step: string
  status: string
  message: string
  timestamp: string
}

interface Knowledge {
  id: number
  title: string
  original_content: string
  summary: string | null
  key_points: string[]
  tags: string[]
  category: string | null
  difficulty: string | null
  action_items: string[]
  usage_example: string | null
  deployment_guide: string | null
  is_open_source: boolean
  repo_url: string | null
  images: string[]
  processing_status: string
  processing_steps: ProcessingStep[]
  is_processed: boolean
  created_at: string | null
  related_ids?: number[]
}

interface Stats {
  total: number
  recent_7_days: number
  processed: number
  unprocessed: number
  categories: Record<string, number>
}

interface SearchResult {
  id: number
  title: string
  summary: string | null
  category: string | null
  tags: string[]
  similarity: number
  snippet: string
}

// 难度星级显示
const DifficultyStars = ({ difficulty }: { difficulty: string | null }) => {
  const levels: Record<string, number> = {
    '简单': 1, '入门': 1,
    '中等': 2, '一般': 2,
    '困难': 3, '高级': 3, '复杂': 3
  }
  const stars = levels[difficulty || ''] || 2
  return (
    <span className="difficulty-stars">
      {[1, 2, 3].map(i => (
        <span key={i} className={i <= stars ? 'star filled' : 'star'}>★</span>
      ))}
      <span className="difficulty-text">{difficulty || '中等'}</span>
    </span>
  )
}

// 丰富的知识卡片组件
const RichKnowledgeCard = ({ 
  knowledge, 
  onClick,
}: { 
  knowledge: Knowledge
  onClick: () => void
}) => {
  const k = knowledge
  
  return (
    <div className="rich-knowledge-card" onClick={onClick}>
      {/* 头部 */}
      <div className="card-top">
        <div className="card-category-badge">
          {k.category || '未分类'}
        </div>
        <DifficultyStars difficulty={k.difficulty} />
      </div>

      {/* 标题 */}
      <h3 className="card-title">{k.title}</h3>

      {/* 摘要 */}
      <p className="card-summary-text">
        {k.summary || k.original_content.slice(0, 120)}...
      </p>

      {/* 关键点预览 */}
      {k.key_points && k.key_points.length > 0 && (
        <div className="card-keypoints">
          <span className="keypoints-label">💡 关键点</span>
          <ul>
            {k.key_points.slice(0, 2).map((point, i) => (
              <li key={i}>{point.length > 30 ? point.slice(0, 30) + '...' : point}</li>
            ))}
            {k.key_points.length > 2 && (
              <li className="more">+{k.key_points.length - 2} 更多</li>
            )}
          </ul>
        </div>
      )}

      {/* 底部信息 */}
      <div className="card-bottom">
        <div className="card-tags">
          {k.tags?.slice(0, 3).map((tag, i) => (
            <span key={i} className="card-tag">{tag}</span>
          ))}
        </div>
        <div className="card-meta">
          {k.is_open_source && <span className="opensource-icon" title="开源项目">🔓</span>}
          {k.is_processed && <span className="processed-icon" title="已蒸馏">✓</span>}
        </div>
      </div>

      {/* 处理状态指示器 */}
      {k.processing_status && k.processing_status !== 'completed' && (
        <div className={`processing-indicator ${k.processing_status}`}>
          {k.processing_status === 'distilling' ? '🔄 蒸馏中...' : 
           k.processing_status === 'embedding' ? '📊 向量化...' : 
           '⏳ 处理中'}
        </div>
      )}
    </div>
  )
}

// 登录页面组件
const LoginPage = ({ onLogin }: { onLogin: () => void }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    // 模拟登录延迟
    setTimeout(() => {
      if (username === AUTH_CONFIG.username && password === AUTH_CONFIG.password) {
        localStorage.setItem('fft_auth', 'true')
        localStorage.setItem('fft_user', username)
        onLogin()
      } else {
        setError('用户名或密码错误')
      }
      setIsLoading(false)
    }, 800)
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">🐕</div>
          <h1>FFT 狗腿子</h1>
          <p className="login-subtitle">Knowledge Distillery</p>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              autoComplete="username"
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoComplete="current-password"
              disabled={isLoading}
            />
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-btn" disabled={isLoading}>
            {isLoading ? (
              <span className="loading-spinner">⏳</span>
            ) : (
              '登 录'
            )}
          </button>
        </form>

        <div className="login-footer">
          <p>AI 驱动的知识蒸馏系统</p>
        </div>
      </div>
    </div>
  )
}

function App() {
  // 认证状态
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  
  // State
  const [view, setView] = useState<'dashboard' | 'add' | 'list' | 'detail' | 'search' | 'graph'>('dashboard')
  const [apiStatus, setApiStatus] = useState<string>('Checking...')
  const [aiStatus, setAiStatus] = useState<string>('Checking...')
  const [stats, setStats] = useState<Stats | null>(null)
  const [knowledgeList, setKnowledgeList] = useState<Knowledge[]>([])
  const [selectedKnowledge, setSelectedKnowledge] = useState<Knowledge | null>(null)
  const [newContent, setNewContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [aiAnswer, setAiAnswer] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [relatedKnowledge, setRelatedKnowledge] = useState<Knowledge[]>([])
  const [viewMode, setViewMode] = useState<'cards' | 'list'>('cards')
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // 检查登录状态
  useEffect(() => {
    const auth = localStorage.getItem('fft_auth')
    if (auth === 'true') {
      setIsAuthenticated(true)
    }
  }, [])

  // Fetch status on mount
  useEffect(() => {
    if (isAuthenticated) {
      checkStatus()
      fetchStats()
      fetchKnowledgeList()
    }
  }, [isAuthenticated])

  const handleLogin = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('fft_auth')
    localStorage.removeItem('fft_user')
    setIsAuthenticated(false)
  }

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/`)
      const data = await res.json()
      setApiStatus(data.message)
    } catch {
      setApiStatus('Backend not connected')
    }

    try {
      const res = await fetch(`${API_BASE}/api/v1/ai/status`)
      const data = await res.json()
      setAiStatus(data.configured ? 'AI Ready ✓' : 'API Key not set')
    } catch {
      setAiStatus('Not available')
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/knowledge/stats`)
      const data = await res.json()
      setStats(data)
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  const fetchKnowledgeList = async (search?: string, category?: string) => {
    try {
      let url = `${API_BASE}/api/v1/knowledge/?limit=100`
      if (search) url += `&search=${encodeURIComponent(search)}`
      if (category) url += `&category=${encodeURIComponent(category)}`
      
      const res = await fetch(url)
      const data = await res.json()
      setKnowledgeList(data)
    } catch (e) {
      console.error('Failed to fetch knowledge list:', e)
    }
  }

  const fetchRelatedKnowledge = async (knowledgeId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/search/similar/${knowledgeId}?limit=5`)
      const data = await res.json()
      
      // Fetch full details for related items
      const relatedDetails = await Promise.all(
        data.similar.map(async (item: any) => {
          const r = await fetch(`${API_BASE}/api/v1/knowledge/${item.id}`)
          return r.json()
        })
      )
      setRelatedKnowledge(relatedDetails)
    } catch (e) {
      console.error('Failed to fetch related knowledge:', e)
      setRelatedKnowledge([])
    }
  }

  const handleAddKnowledge = async () => {
    // 允许仅上传图片或仅输入文字
    const hasContent = newContent.trim().length > 0
    const hasImages = uploadedImages.length > 0
    
    if (!hasContent && !hasImages) {
      alert('请输入内容或上传图片')
      return
    }
    
    setIsLoading(true)
    try {
      // 将上传的图片 URL 转换为相对路径供后端分析
      const imagePathsForBackend = uploadedImages.map(url => {
        // 提取相对路径 /api/v1/upload/images/xxx.jpg
        const match = url.match(/\/api\/v1\/upload\/images\/[^/]+$/)
        return match ? match[0] : url
      })
      
      const res = await fetch(`${API_BASE}/api/v1/knowledge/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          content: newContent,
          images: imagePathsForBackend,
          source_type: hasImages && !hasContent ? 'image' : 'manual',
          auto_process: true 
        })
      })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || '创建失败')
      }
      
      const data = await res.json()
      setNewContent('')
      setUploadedImages([])
      setSelectedKnowledge(data)
      setView('detail')
      fetchStats()
      fetchKnowledgeList()
    } catch (e) {
      console.error('Failed to add knowledge:', e)
      alert(`添加失败: ${e instanceof Error ? e.message : '请重试'}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = () => {
    fetchKnowledgeList(searchTerm, filterCategory)
  }

  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) return
    
    setIsSearching(true)
    setAiAnswer(null)
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/search/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: searchQuery, 
          limit: 10,
          include_answer: true 
        })
      })
      const data = await res.json()
      setSearchResults(data.results || [])
      setAiAnswer(data.answer || null)
    } catch (e) {
      console.error('Search failed:', e)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleSendReport = async () => {
    if (!confirm('确定要发送每日报告邮件吗？')) return
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/reports/send/daily`, { method: 'POST' })
      const data = await res.json()
      alert(`报告发送中！收件人: ${data.recipients.join(', ')}`)
    } catch (e) {
      console.error('Failed to send report:', e)
      alert('发送失败，请检查邮件配置')
    }
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    
    setIsUploading(true)
    const formData = new FormData()
    
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i])
    }
    
    try {
      const res = await fetch(`${API_BASE}/api/v1/upload/images/batch`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      
      const newUrls = data.results
        .filter((r: any) => r.status === 'success')
        .map((r: any) => `${API_BASE}${r.url}`)
      
      setUploadedImages(prev => [...prev, ...newUrls])
    } catch (e) {
      console.error('Upload failed:', e)
      alert('图片上传失败')
    } finally {
      setIsUploading(false)
    }
  }

  const removeImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这条知识吗？')) return
    
    try {
      await fetch(`${API_BASE}/api/v1/knowledge/${id}`, { method: 'DELETE' })
      setView('list')
      fetchStats()
      fetchKnowledgeList()
    } catch (e) {
      console.error('Failed to delete:', e)
    }
  }

  const openKnowledgeDetail = async (knowledge: Knowledge) => {
    setSelectedKnowledge(knowledge)
    setView('detail')
    setMobileMenuOpen(false)
    await fetchRelatedKnowledge(knowledge.id)
  }

  const navigateTo = (newView: typeof view) => {
    setView(newView)
    setMobileMenuOpen(false)
  }

  // 如果未登录，显示登录页面
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  // Render Dashboard
  const renderDashboard = () => (
    <div className="dashboard">
      <div className="stats-grid">
        <div className="stat-card primary" onClick={() => navigateTo('list')}>
          <div className="stat-number">{stats?.total || 0}</div>
          <div className="stat-label">📚 总知识量</div>
        </div>
        <div className="stat-card success">
          <div className="stat-number">{stats?.recent_7_days || 0}</div>
          <div className="stat-label">✨ 本周新增</div>
        </div>
        <div className="stat-card info">
          <div className="stat-number">{stats?.processed || 0}</div>
          <div className="stat-label">🧪 已蒸馏</div>
        </div>
        <div className="stat-card warning" onClick={() => navigateTo('graph')}>
          <div className="stat-number">{Object.keys(stats?.categories || {}).length}</div>
          <div className="stat-label">📂 分类数</div>
        </div>
      </div>

      <div className="status-section">
        <h3>系统状态</h3>
        <div className="status-grid">
          <div className="status-item">
            <span>Frontend</span>
            <span className="badge online">Online ✓</span>
          </div>
          <div className="status-item">
            <span>Backend</span>
            <span className={`badge ${apiStatus.includes('running') ? 'online' : 'offline'}`}>
              {apiStatus.includes('running') ? 'Online ✓' : 'Offline'}
            </span>
          </div>
          <div className="status-item">
            <span>AI Service</span>
            <span className={`badge ${aiStatus.includes('Ready') ? 'online' : 'pending'}`}>
              {aiStatus}
            </span>
          </div>
        </div>
      </div>

      {stats?.categories && Object.keys(stats.categories).length > 0 && (
        <div className="categories-section">
          <h3>知识分类</h3>
          <div className="category-tags">
            {Object.entries(stats.categories).map(([cat, count]) => (
              <span 
                key={cat} 
                className="category-tag clickable"
                onClick={() => { setFilterCategory(cat); navigateTo('list'); }}
              >
                {cat} <span className="count">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 最近知识预览 */}
      {knowledgeList.length > 0 && (
        <div className="recent-section">
          <h3>最近添加</h3>
          <div className="recent-cards">
            {knowledgeList.slice(0, 3).map(k => (
              <RichKnowledgeCard 
                key={k.id} 
                knowledge={k} 
                onClick={() => openKnowledgeDetail(k)}
              />
            ))}
          </div>
        </div>
      )}

      <div className="actions-section">
        <h3>快捷操作</h3>
        <div className="quick-actions">
          <button className="btn primary" onClick={() => navigateTo('add')}>
            ➕ 添加知识
          </button>
          <button className="btn secondary" onClick={() => navigateTo('search')}>
            🔍 智能搜索
          </button>
          <button className="btn secondary" onClick={() => navigateTo('graph')}>
            📊 知识图谱
          </button>
          <button className="btn secondary" onClick={handleSendReport}>
            📧 发送报告
          </button>
        </div>
      </div>
    </div>
  )

  // Render Add Knowledge Form
  const renderAddForm = () => {
    const hasContent = newContent.trim().length > 0
    const hasImages = uploadedImages.length > 0
    const canSubmit = hasContent || hasImages
    
    return (
    <div className="add-form">
      <h2>➕ 添加新知识</h2>
      <p className="form-hint">
        📝 输入文字 或 📷 上传截图，AI 将自动分析并生成知识卡片
      </p>
      
      {/* Image Upload Section - 放在前面突出 */}
      <div className="image-upload-section primary">
        <div className="upload-header">
          <span className="upload-title">📷 上传截图</span>
          <span className="upload-hint">支持开源项目页面、代码截图、文档等</span>
        </div>
        <label className="upload-btn">
          {isUploading ? '上传中...' : '选择图片'}
          <input 
            type="file" 
            accept="image/*" 
            multiple 
            onChange={handleImageUpload}
            disabled={isUploading || isLoading}
          />
        </label>
        
        {uploadedImages.length > 0 && (
          <div className="uploaded-images">
            {uploadedImages.map((url, index) => (
              <div key={index} className="uploaded-image-item">
                <img src={url} alt={`Upload ${index + 1}`} />
                <button onClick={() => removeImage(index)}>×</button>
              </div>
            ))}
            <p className="image-count">已上传 {uploadedImages.length} 张图片，AI 将分析图片内容</p>
          </div>
        )}
      </div>

      <div className="or-divider">
        <span>或</span>
      </div>
      
      <textarea
        value={newContent}
        onChange={(e) => setNewContent(e.target.value)}
        placeholder="在此输入或粘贴文字内容...&#10;&#10;如果已上传截图，此处可留空"
        rows={6}
        disabled={isLoading}
      />

      {/* Processing Steps Preview */}
      {isLoading && (
        <div className="processing-preview">
          <h4>🔄 AI 正在处理...</h4>
          <div className="processing-steps">
            <div className="step active">✓ 创建知识条目</div>
            <div className="step active">✓ 验证内容</div>
            {hasImages && <div className="step processing">⏳ 分析图片内容...</div>}
            <div className={`step ${hasImages ? 'pending' : 'processing'}`}>
              {hasImages ? '○' : '⏳'} AI 蒸馏知识...
            </div>
            <div className="step pending">○ 生成向量嵌入</div>
            <div className="step pending">○ 完成</div>
          </div>
        </div>
      )}
      
      <div className="form-actions">
        <button 
          className="btn primary" 
          onClick={handleAddKnowledge}
          disabled={isLoading || !canSubmit}
        >
          {isLoading ? '🔄 AI 处理中...' : hasImages && !hasContent ? '🔍 分析图片' : '🧪 蒸馏知识'}
        </button>
        <button className="btn secondary" onClick={() => { navigateTo('dashboard'); setUploadedImages([]); }}>
          取消
        </button>
      </div>
    </div>
  )}

  // Render Knowledge List with Rich Cards
  const renderList = () => (
    <div className="knowledge-list">
      <div className="list-header">
        <h2>📚 知识库</h2>
        <div className="list-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder="搜索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch}>🔍</button>
          </div>
          <select 
            value={filterCategory} 
            onChange={(e) => { setFilterCategory(e.target.value); fetchKnowledgeList(searchTerm, e.target.value); }}
            className="category-filter"
          >
            <option value="">全部</option>
            {Object.keys(stats?.categories || {}).map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {knowledgeList.length === 0 ? (
        <div className="empty-state">
          <p>📭 暂无知识</p>
          <button className="btn primary" onClick={() => navigateTo('add')}>
            添加第一条知识
          </button>
        </div>
      ) : (
        <div className="knowledge-cards-grid">
          {knowledgeList.map((k) => (
            <RichKnowledgeCard 
              key={k.id} 
              knowledge={k} 
              onClick={() => openKnowledgeDetail(k)}
            />
          ))}
        </div>
      )}
    </div>
  )

  // Render Knowledge Detail with Related Knowledge
  const renderDetail = () => {
    if (!selectedKnowledge) return null
    const k = selectedKnowledge

    return (
      <div className="knowledge-detail">
        <button className="back-btn" onClick={() => navigateTo('list')}>
          ← 返回列表
        </button>

        <div className="detail-header">
          <h1>{k.title}</h1>
          <div className="detail-meta">
            <span className="category-badge">{k.category || '未分类'}</span>
            <DifficultyStars difficulty={k.difficulty} />
            {k.is_open_source && <span className="opensource-badge">🔓 开源</span>}
          </div>
        </div>

        {k.summary && (
          <div className="detail-section">
            <h3>📝 摘要</h3>
            <p>{k.summary}</p>
          </div>
        )}

        {k.key_points?.length > 0 && (
          <div className="detail-section highlight-section">
            <h3>💡 关键点</h3>
            <ul className="key-points">
              {k.key_points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Usage Example */}
        {k.usage_example && (
          <div className="detail-section code-section">
            <h3>💻 使用示例</h3>
            <pre className="code-block">{k.usage_example}</pre>
          </div>
        )}

        {/* Deployment Guide */}
        {k.deployment_guide && (
          <div className="detail-section">
            <h3>🚀 部署指南</h3>
            <pre className="code-block">{k.deployment_guide}</pre>
          </div>
        )}

        {/* Repository URL */}
        {k.repo_url && (
          <div className="detail-section">
            <h3>📦 仓库地址</h3>
            <a href={k.repo_url} target="_blank" rel="noopener noreferrer" className="repo-link">
              {k.repo_url}
            </a>
          </div>
        )}

        {k.action_items?.length > 0 && (
          <div className="detail-section">
            <h3>✅ 行动建议</h3>
            <ul className="action-items">
              {k.action_items.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Related Knowledge */}
        {relatedKnowledge.length > 0 && (
          <div className="detail-section related-section">
            <h3>🔗 相关知识</h3>
            <div className="related-cards">
              {relatedKnowledge.map(rk => (
                <div 
                  key={rk.id} 
                  className="related-card"
                  onClick={() => openKnowledgeDetail(rk)}
                >
                  <h4>{rk.title}</h4>
                  <p>{rk.summary?.slice(0, 50) || rk.original_content.slice(0, 50)}...</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Images */}
        {k.images?.length > 0 && (
          <div className="detail-section">
            <h3>📷 附件图片</h3>
            <div className="image-gallery">
              {k.images.map((url, i) => (
                <img key={i} src={url} alt={`Image ${i + 1}`} onClick={() => window.open(url, '_blank')} />
              ))}
            </div>
          </div>
        )}

        {k.tags?.length > 0 && (
          <div className="detail-section">
            <h3>🏷️ 标签</h3>
            <div className="tags-list">
              {k.tags.map((tag, i) => (
                <span key={i} className="tag large">{tag}</span>
              ))}
            </div>
          </div>
        )}

        <div className="detail-section">
          <h3>📄 原始内容</h3>
          <div className="original-content">
            {k.original_content}
          </div>
        </div>

        <div className="detail-actions">
          <button className="btn danger" onClick={() => handleDelete(k.id)}>
            🗑️ 删除
          </button>
        </div>
      </div>
    )
  }

  // Render Semantic Search
  const renderSearch = () => (
    <div className="search-view">
      <h2>🔍 智能搜索</h2>
      <p className="form-hint">输入问题，AI 将从知识库中找到答案</p>
      
      <div className="search-input-group">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSemanticSearch()}
          placeholder="输入您的问题..."
          disabled={isSearching}
        />
        <button 
          className="btn primary" 
          onClick={handleSemanticSearch}
          disabled={isSearching || !searchQuery.trim()}
        >
          {isSearching ? '...' : '搜索'}
        </button>
      </div>

      {aiAnswer && (
        <div className="ai-answer-card">
          <h3>🤖 AI 回答</h3>
          <p>{aiAnswer}</p>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="search-results">
          <h3>📚 相关知识 ({searchResults.length})</h3>
          {searchResults.map((result) => (
            <div 
              key={result.id} 
              className="search-result-card"
              onClick={async () => {
                const res = await fetch(`${API_BASE}/api/v1/knowledge/${result.id}`)
                const data = await res.json()
                openKnowledgeDetail(data)
              }}
            >
              <div className="result-header">
                <h4>{result.title}</h4>
                <span className="similarity">{Math.round(result.similarity * 100)}%</span>
              </div>
              <p className="result-snippet">{result.snippet}</p>
              <div className="result-meta">
                <span className="category">{result.category || '未分类'}</span>
                {result.tags?.slice(0, 2).map((tag, i) => (
                  <span key={i} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!isSearching && searchQuery && searchResults.length === 0 && (
        <div className="empty-state">
          <p>未找到相关知识</p>
          <button className="btn primary" onClick={() => navigateTo('add')}>
            添加新知识
          </button>
        </div>
      )}
    </div>
  )

  // Render Knowledge Graph (Simple version)
  const renderGraph = () => (
    <div className="graph-view">
      <h2>📊 知识图谱</h2>
      <p className="form-hint">可视化知识点关联</p>
      
      <div className="graph-container">
        <div className="graph-categories">
          {Object.entries(stats?.categories || {}).map(([category, count]) => (
            <div key={category} className="graph-category-node">
              <div className="category-circle" style={{ 
                width: Math.min(120, 50 + count * 12),
                height: Math.min(120, 50 + count * 12)
              }}>
                <span className="category-name">{category}</span>
                <span className="category-count">{count}</span>
              </div>
              <div className="category-items">
                {knowledgeList
                  .filter(k => k.category === category)
                  .slice(0, 3)
                  .map(k => (
                    <div 
                      key={k.id} 
                      className="graph-knowledge-node"
                      onClick={() => openKnowledgeDetail(k)}
                    >
                      {k.title.slice(0, 15)}...
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="graph-legend">
        <h4>标签云</h4>
        <div className="tag-cloud">
          {Array.from(new Set(knowledgeList.flatMap(k => k.tags || []))).slice(0, 20).map((tag, i) => {
            const count = knowledgeList.filter(k => k.tags?.includes(tag)).length
            return (
              <span 
                key={i} 
                className="cloud-tag"
                style={{ fontSize: `${Math.min(1.3, 0.8 + count * 0.1)}rem` }}
                onClick={() => { setSearchTerm(tag); navigateTo('list'); handleSearch(); }}
              >
                {tag}
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )

  return (
    <div className="app">
      {/* Mobile Header */}
      <header className="mobile-header">
        <div className="header-left">
          <span className="header-logo">🐕</span>
          <span className="header-title">FFT 狗腿子</span>
        </div>
        <button 
          className="menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? '✕' : '☰'}
        </button>
      </header>

      {/* Navigation Menu */}
      <nav className={`navbar ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="nav-brand" onClick={() => navigateTo('dashboard')}>
          <span className="logo">🐕</span>
          <span className="brand-text">FFT 狗腿子</span>
        </div>
        <div className="nav-links">
          <button 
            className={view === 'dashboard' ? 'active' : ''} 
            onClick={() => navigateTo('dashboard')}
          >
            📊 仪表盘
          </button>
          <button 
            className={view === 'list' ? 'active' : ''} 
            onClick={() => navigateTo('list')}
          >
            📚 知识库
          </button>
          <button 
            className={view === 'search' ? 'active' : ''} 
            onClick={() => navigateTo('search')}
          >
            🔍 搜索
          </button>
          <button 
            className={view === 'graph' ? 'active' : ''} 
            onClick={() => navigateTo('graph')}
          >
            📊 图谱
          </button>
          <button 
            className={view === 'add' ? 'active' : ''} 
            onClick={() => navigateTo('add')}
          >
            ➕ 添加
          </button>
          <button 
            className="logout-btn"
            onClick={handleLogout}
          >
            🚪 退出
          </button>
        </div>
      </nav>

      {/* Overlay for mobile menu */}
      {mobileMenuOpen && (
        <div className="nav-overlay" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* Main Content */}
      <main className="main-content">
        {view === 'dashboard' && renderDashboard()}
        {view === 'add' && renderAddForm()}
        {view === 'list' && renderList()}
        {view === 'detail' && renderDetail()}
        {view === 'search' && renderSearch()}
        {view === 'graph' && renderGraph()}
      </main>

      {/* Bottom Navigation for Mobile */}
      <nav className="bottom-nav">
        <button 
          className={view === 'dashboard' ? 'active' : ''} 
          onClick={() => navigateTo('dashboard')}
        >
          <span className="nav-icon">📊</span>
          <span className="nav-label">首页</span>
        </button>
        <button 
          className={view === 'list' ? 'active' : ''} 
          onClick={() => navigateTo('list')}
        >
          <span className="nav-icon">📚</span>
          <span className="nav-label">知识库</span>
        </button>
        <button 
          className={view === 'add' ? 'active' : ''} 
          onClick={() => navigateTo('add')}
        >
          <span className="nav-icon add-icon">➕</span>
          <span className="nav-label">添加</span>
        </button>
        <button 
          className={view === 'search' ? 'active' : ''} 
          onClick={() => navigateTo('search')}
        >
          <span className="nav-icon">🔍</span>
          <span className="nav-label">搜索</span>
        </button>
        <button 
          className={view === 'graph' ? 'active' : ''} 
          onClick={() => navigateTo('graph')}
        >
          <span className="nav-icon">📊</span>
          <span className="nav-label">图谱</span>
        </button>
      </nav>
    </div>
  )
}

export default App
