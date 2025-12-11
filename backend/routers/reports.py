"""
Reports API Router
Manual report triggers and scheduling management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.scheduler_service import (
    trigger_daily_report_now,
    trigger_weekly_report_now,
    scheduler
)
from services.knowledge_service import knowledge_service
from services.ai_service import ai_service
from services.email_service import email_service
from config import settings

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


class ReportPreview(BaseModel):
    """Report preview response"""
    title: str
    overview: str
    highlights: List[str]
    stats: dict
    recipients: List[str]


@router.get("/preview/daily")
async def preview_daily_report(db: AsyncSession = Depends(get_db)):
    """
    Preview the daily report without sending
    
    Returns what would be sent in the daily email
    """
    # Get recent knowledge
    recent_items = await knowledge_service.get_recent_for_digest(db, days=1)
    
    if not recent_items:
        return {
            "title": "每日知识摘要",
            "overview": "今日暂无新知识入库",
            "highlights": [],
            "stats": {"total": 0, "new_today": 0},
            "recipients": settings.recipient_list,
            "items_count": 0
        }
    
    # Generate digest
    digest = await ai_service.generate_daily_digest(recent_items)
    stats = await knowledge_service.get_stats(db)
    
    return {
        "title": digest.get("title", "每日知识摘要"),
        "overview": digest.get("overview", ""),
        "highlights": digest.get("highlights", []),
        "recommendation": digest.get("recommendation", ""),
        "stats": {
            "total": stats.get("total", 0),
            "new_today": len(recent_items),
            "categories": stats.get("categories", {})
        },
        "recipients": settings.recipient_list,
        "items_count": len(recent_items),
        "items": [
            {"title": item.get("title"), "category": item.get("category")}
            for item in recent_items[:10]
        ]
    }


@router.post("/send/daily")
async def send_daily_report_now(background_tasks: BackgroundTasks):
    """
    Manually trigger daily report email
    
    Sends the daily digest immediately to configured recipients
    """
    if not settings.recipient_list:
        raise HTTPException(status_code=400, detail="No email recipients configured")
    
    background_tasks.add_task(trigger_daily_report_now)
    
    return {
        "status": "sending",
        "message": "Daily report is being generated and sent",
        "recipients": settings.recipient_list
    }


@router.post("/send/weekly")
async def send_weekly_report_now(background_tasks: BackgroundTasks):
    """
    Manually trigger weekly report email
    
    Sends the weekly digest immediately to configured recipients
    """
    if not settings.recipient_list:
        raise HTTPException(status_code=400, detail="No email recipients configured")
    
    background_tasks.add_task(trigger_weekly_report_now)
    
    return {
        "status": "sending",
        "message": "Weekly report is being generated and sent",
        "recipients": settings.recipient_list
    }


@router.get("/schedule")
async def get_schedule_info():
    """Get information about scheduled reports"""
    jobs = []
    
    if scheduler and scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
    
    return {
        "scheduler_running": scheduler is not None and scheduler.running,
        "jobs": jobs,
        "email_configured": bool(settings.smtp_user and settings.smtp_password),
        "recipients": settings.recipient_list
    }


@router.post("/test-email")
async def send_test_email():
    """Send a test email to verify configuration"""
    if not settings.recipient_list:
        raise HTTPException(status_code=400, detail="No email recipients configured")
    
    result = await email_service.send_test_email(settings.recipient_list[0])
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

