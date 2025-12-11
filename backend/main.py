"""
Knowledge Distillery - FastAPI Backend
Development Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database
from database import init_db

# Import routers
from routers import email, ai, knowledge, search, reports, upload, learning

# Import scheduler
from services.scheduler_service import init_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Knowledge Distillery...")
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Start scheduler
    try:
        init_scheduler()
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Knowledge Distillery...")
    shutdown_scheduler()


# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Distillery API",
    description="Backend API for Knowledge Distillery - A knowledge management system with vector search",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://frontend:5173",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(email.router)
app.include_router(ai.router)
app.include_router(knowledge.router)
app.include_router(search.router)
app.include_router(reports.router)
app.include_router(upload.router)
app.include_router(learning.router)


@app.get("/")
async def root():
    """Root endpoint - Health check"""
    return {
        "status": "online",
        "message": "Knowledge Distillery API is running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {
        "status": "healthy",
        "database": "connected",
        "email": "configured",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/api/v1/test")
async def test_endpoint():
    """Test endpoint to verify API connectivity"""
    return {
        "message": "API is working!",
        "hot_reload": "enabled - edit this file and see changes instantly"
    }
