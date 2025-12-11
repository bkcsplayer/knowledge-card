"""
Knowledge model with vector embedding support
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from database import Base


class Knowledge(Base):
    """
    Knowledge entry model
    Stores distilled knowledge with vector embeddings for semantic search
    """
    __tablename__ = "knowledge"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core content
    title = Column(String(500), nullable=False, index=True)
    original_content = Column(Text, nullable=False)  # Raw input content
    summary = Column(Text)  # AI-generated summary
    
    # Distilled metadata (from AI)
    key_points = Column(JSONB, default=list)  # List of key points
    tags = Column(JSONB, default=list)  # List of tags
    category = Column(String(100), index=True)
    difficulty = Column(String(50))
    action_items = Column(JSONB, default=list)  # Suggested actions
    
    # Usage and deployment info (for code/projects)
    usage_example = Column(Text, nullable=True)  # How to use
    deployment_guide = Column(Text, nullable=True)  # How to deploy (for open source)
    is_open_source = Column(Boolean, default=False)
    repo_url = Column(String(500), nullable=True)  # GitHub/GitLab URL
    
    # Attached images
    images = Column(JSONB, default=list)  # List of image URLs
    
    # Processing status tracking
    processing_status = Column(String(50), default="pending")  # pending, validating, distilling, embedding, completed, failed
    processing_steps = Column(JSONB, default=list)  # List of completed steps with timestamps
    
    # Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    embedding = Column(Vector(1536), nullable=True)
    
    # Source information
    source_type = Column(String(50), default="manual")  # manual, url, file, api
    source_url = Column(String(2000), nullable=True)
    
    # Status
    is_processed = Column(Boolean, default=False)  # AI processing completed
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Create indexes for efficient querying
    __table_args__ = (
        Index('idx_knowledge_tags', 'tags', postgresql_using='gin', postgresql_ops={'tags': 'jsonb_path_ops'}),
        Index('idx_knowledge_created', 'created_at'),
    )
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "original_content": self.original_content,
            "summary": self.summary,
            "key_points": self.key_points or [],
            "tags": self.tags or [],
            "category": self.category,
            "difficulty": self.difficulty,
            "action_items": self.action_items or [],
            "usage_example": self.usage_example,
            "deployment_guide": self.deployment_guide,
            "is_open_source": self.is_open_source,
            "repo_url": self.repo_url,
            "images": self.images or [],
            "processing_status": self.processing_status,
            "processing_steps": self.processing_steps or [],
            "source_type": self.source_type,
            "source_url": self.source_url,
            "is_processed": self.is_processed,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

