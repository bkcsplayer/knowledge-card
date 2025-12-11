"""
Email API Router
Endpoints for sending emails and managing email settings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from services.email_service import email_service
from config import settings

router = APIRouter(prefix="/api/v1/email", tags=["Email"])


class SendEmailRequest(BaseModel):
    """Request model for sending custom emails"""
    to_emails: List[EmailStr]
    subject: str
    body_html: str
    body_text: Optional[str] = None


class SendSummaryRequest(BaseModel):
    """Request model for sending summary reports"""
    to_emails: Optional[List[EmailStr]] = None  # Use default recipients if not provided
    summary_data: Optional[dict] = None  # Use default data if not provided


class TestEmailRequest(BaseModel):
    """Request model for test email"""
    to_email: Optional[EmailStr] = None  # Use default if not provided


@router.get("/config")
async def get_email_config():
    """Get current email configuration (without sensitive data)"""
    return {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_user": settings.smtp_user,
        "smtp_from": settings.smtp_from,
        "smtp_from_name": settings.smtp_from_name,
        "default_recipients": settings.recipient_list,
        "configured": bool(settings.smtp_user and settings.smtp_password)
    }


@router.post("/test")
async def send_test_email(request: TestEmailRequest = None):
    """
    Send a test email to verify SMTP configuration
    
    If no email is provided, sends to the default recipient
    """
    to_email = request.to_email if request and request.to_email else settings.smtp_from
    
    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient email configured")
    
    result = await email_service.send_test_email(to_email)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.post("/send")
async def send_custom_email(request: SendEmailRequest):
    """Send a custom email"""
    result = await email_service.send_email(
        to_emails=request.to_emails,
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.post("/summary")
async def send_summary_report(request: SendSummaryRequest = None):
    """
    Send daily knowledge summary report
    
    If no recipients provided, uses default recipients from config
    If no summary data provided, uses placeholder data
    """
    # Use default recipients if not provided
    recipients = request.to_emails if request and request.to_emails else settings.recipient_list
    
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients configured")
    
    # Use provided data or generate placeholder
    summary_data = request.summary_data if request and request.summary_data else {
        "total_documents": 0,
        "new_today": 0,
        "total_queries": 0,
        "active_users": 1,
        "highlight_title": "系统初始化完成",
        "highlight_description": "Knowledge Distillery 已成功部署，等待添加知识库内容。",
        "top_topics": ["系统配置", "邮件服务", "数据库连接"],
        "dashboard_url": "http://localhost:5173"
    }
    
    result = await email_service.send_daily_summary(recipients, summary_data)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result


@router.get("/recipients")
async def get_default_recipients():
    """Get list of default email recipients"""
    return {
        "recipients": settings.recipient_list,
        "count": len(settings.recipient_list)
    }

