"""
Email Service for Knowledge Distillery
Handles sending reports and summaries via SMTP
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP Email Service for sending reports and notifications"""
    
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from
        self.from_name = settings.smtp_from_name
    
    def _create_connection(self):
        """Create SMTP connection with TLS"""
        context = ssl.create_default_context()
        server = smtplib.SMTP(self.host, self.port)
        server.starttls(context=context)
        server.login(self.user, self.password)
        return server
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> dict:
        """
        Send an email with HTML content
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            body_html: HTML content of the email
            body_text: Plain text fallback (optional)
            attachments: List of {"filename": str, "content": bytes} dicts
        
        Returns:
            dict with status and message
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = ", ".join(to_emails)
            
            # Add plain text version
            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            
            # Add HTML version
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}"
                    )
                    msg.attach(part)
            
            # Send email
            with self._create_connection() as server:
                server.sendmail(self.from_email, to_emails, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_emails}")
            return {"status": "success", "message": f"Email sent to {len(to_emails)} recipient(s)"}
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return {"status": "error", "message": "SMTP authentication failed. Check credentials."}
        
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {"status": "error", "message": f"SMTP error: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}
    
    async def send_daily_summary(
        self,
        to_emails: List[str],
        summary_data: dict
    ) -> dict:
        """
        Send daily knowledge summary report
        
        Args:
            to_emails: List of recipient emails
            summary_data: Dictionary containing summary information
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        subject = f"📚 Knowledge Distillery - 每日知识总结 ({today})"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0; opacity: 0.8; }}
                .content {{ padding: 30px; }}
                .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 25px; }}
                .stat-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; }}
                .stat-number {{ font-size: 32px; font-weight: bold; color: #00d9ff; }}
                .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
                .section {{ margin-bottom: 25px; }}
                .section h2 {{ color: #1a1a2e; font-size: 18px; border-bottom: 2px solid #00d9ff; padding-bottom: 10px; }}
                .item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; }}
                .item-title {{ font-weight: bold; color: #333; }}
                .item-meta {{ color: #888; font-size: 12px; margin-top: 5px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #888; font-size: 12px; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #00d9ff 0%, #00ff88 100%); color: #1a1a2e; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 Knowledge Distillery</h1>
                    <p>每日知识总结报告 - {today}</p>
                </div>
                
                <div class="content">
                    <div class="stat-grid">
                        <div class="stat-card">
                            <div class="stat-number">{summary_data.get('total_documents', 0)}</div>
                            <div class="stat-label">📄 总文档数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{summary_data.get('new_today', 0)}</div>
                            <div class="stat-label">✨ 今日新增</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{summary_data.get('total_queries', 0)}</div>
                            <div class="stat-label">🔍 总查询次数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{summary_data.get('active_users', 0)}</div>
                            <div class="stat-label">👥 活跃用户</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>📌 今日要点</h2>
                        <div class="item">
                            <div class="item-title">{summary_data.get('highlight_title', '暂无要点')}</div>
                            <div class="item-meta">{summary_data.get('highlight_description', '系统正在收集数据...')}</div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>🔥 热门主题</h2>
                        {''.join([f'<div class="item"><div class="item-title">{topic}</div></div>' for topic in summary_data.get('top_topics', ['暂无数据'])])}
                    </div>
                    
                    <center>
                        <a href="{summary_data.get('dashboard_url', '#')}" class="btn">查看完整报告 →</a>
                    </center>
                </div>
                
                <div class="footer">
                    <p>此邮件由 Knowledge Distillery 系统自动发送</p>
                    <p>© 2024 Knowledge Distillery. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Knowledge Distillery - 每日知识总结 ({today})
        ================================================
        
        📊 统计数据:
        - 总文档数: {summary_data.get('total_documents', 0)}
        - 今日新增: {summary_data.get('new_today', 0)}
        - 总查询次数: {summary_data.get('total_queries', 0)}
        - 活跃用户: {summary_data.get('active_users', 0)}
        
        📌 今日要点:
        {summary_data.get('highlight_title', '暂无要点')}
        {summary_data.get('highlight_description', '')}
        
        🔥 热门主题:
        {chr(10).join(['- ' + topic for topic in summary_data.get('top_topics', ['暂无数据'])])}
        
        ---
        此邮件由 Knowledge Distillery 系统自动发送
        """
        
        return await self.send_email(to_emails, subject, body_html, body_text)
    
    async def send_test_email(self, to_email: str) -> dict:
        """Send a test email to verify SMTP configuration"""
        subject = "🧪 Knowledge Distillery - 测试邮件"
        
        body_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
                .container { max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; text-align: center; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #1a1a2e; }
                p { color: #666; }
                .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1>邮件配置成功!</h1>
                <p>您的 SMTP 邮件服务已正确配置。</p>
                <div class="success">
                    <strong>Knowledge Distillery</strong> 现在可以发送报告和通知了。
                </div>
            </div>
        </body>
        </html>
        """
        
        body_text = """
        ✅ 邮件配置成功!
        
        您的 SMTP 邮件服务已正确配置。
        Knowledge Distillery 现在可以发送报告和通知了。
        """
        
        return await self.send_email([to_email], subject, body_html, body_text)


# Global email service instance
email_service = EmailService()

