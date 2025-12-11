"""
Scheduler Service for Knowledge Distillery
Handles scheduled tasks like daily email reports
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def send_daily_report():
    """
    Send daily knowledge digest via email
    This function is called by the scheduler
    """
    from database import AsyncSessionLocal
    from services.knowledge_service import knowledge_service
    from services.ai_service import ai_service
    from services.email_service import email_service
    
    logger.info("📧 Starting daily report generation...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Get recent knowledge entries
            recent_items = await knowledge_service.get_recent_for_digest(db, days=1)
            
            if not recent_items:
                logger.info("No new knowledge today, skipping email")
                return
            
            # Generate AI digest
            digest = await ai_service.generate_daily_digest(recent_items)
            
            # Get stats
            stats = await knowledge_service.get_stats(db)
            
            # Prepare email data
            summary_data = {
                "total_documents": stats.get("total", 0),
                "new_today": len(recent_items),
                "total_queries": 0,  # Can be tracked separately
                "active_users": 1,
                "highlight_title": digest.get("title", "每日知识摘要"),
                "highlight_description": digest.get("overview", ""),
                "top_topics": digest.get("highlights", []),
                "dashboard_url": f"http://{settings.smtp_from.split('@')[1] if '@' in settings.smtp_from else 'localhost'}:5173"
            }
            
            # Send email
            recipients = settings.recipient_list
            if recipients:
                result = await email_service.send_daily_summary(recipients, summary_data)
                logger.info(f"Daily report sent: {result}")
            else:
                logger.warning("No email recipients configured")
                
    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")


async def send_weekly_report():
    """Send weekly knowledge digest"""
    from database import AsyncSessionLocal
    from services.knowledge_service import knowledge_service
    from services.ai_service import ai_service
    from services.email_service import email_service
    
    logger.info("📧 Starting weekly report generation...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Get knowledge from past 7 days
            recent_items = await knowledge_service.get_recent_for_digest(db, days=7, limit=50)
            
            if not recent_items:
                logger.info("No new knowledge this week, skipping email")
                return
            
            # Generate digest
            digest = await ai_service.generate_daily_digest(recent_items)
            
            # Get stats
            stats = await knowledge_service.get_stats(db)
            
            summary_data = {
                "total_documents": stats.get("total", 0),
                "new_today": len(recent_items),
                "total_queries": 0,
                "active_users": 1,
                "highlight_title": f"本周知识回顾 - {datetime.now().strftime('%Y年%m月%d日')}",
                "highlight_description": digest.get("overview", ""),
                "top_topics": digest.get("highlights", []),
                "dashboard_url": "http://localhost:5173"
            }
            
            recipients = settings.recipient_list
            if recipients:
                result = await email_service.send_daily_summary(recipients, summary_data)
                logger.info(f"Weekly report sent: {result}")
                
    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")


def init_scheduler():
    """Initialize and start the scheduler"""
    global scheduler
    
    if scheduler is not None:
        return scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Daily report at 9:00 AM
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=9, minute=0),
        id="daily_report",
        name="Daily Knowledge Digest",
        replace_existing=True
    )
    
    # Weekly report on Monday at 9:00 AM
    scheduler.add_job(
        send_weekly_report,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_report",
        name="Weekly Knowledge Digest",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("📅 Scheduler started - Daily report at 9:00 AM, Weekly report on Monday 9:00 AM")
    
    return scheduler


def shutdown_scheduler():
    """Shutdown the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler shutdown")


async def trigger_daily_report_now():
    """Manually trigger daily report (for testing)"""
    await send_daily_report()


async def trigger_weekly_report_now():
    """Manually trigger weekly report (for testing)"""
    await send_weekly_report()

