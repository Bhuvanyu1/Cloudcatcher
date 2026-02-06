"""
Email Service for CloudWatcher using Resend
- Email verification
- Password reset
- Alert notifications
"""
import os
import asyncio
import logging
import resend
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize Resend
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
APP_NAME = "CloudWatcher"
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# ==================== EMAIL TEMPLATES ====================

def get_verification_email_html(name: str, verification_link: str) -> str:
    """Generate email verification HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #000; font-family: 'Courier New', monospace;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #000; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; border: 2px solid #333;">
                        <tr>
                            <td style="padding: 40px; border-bottom: 2px solid #333;">
                                <h1 style="margin: 0; color: #fff; font-size: 24px; font-weight: bold;">
                                    CLOUD<span style="color: #CCFF00;">WATCHER</span>
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px 0; color: #fff; font-size: 20px;">
                                    Verify Your Email
                                </h2>
                                <p style="margin: 0 0 20px 0; color: #888; font-size: 14px; line-height: 1.6;">
                                    Hi {name},<br><br>
                                    Welcome to CloudWatcher! Please verify your email address to complete your registration.
                                </p>
                                <a href="{verification_link}" 
                                   style="display: inline-block; padding: 15px 30px; background-color: #CCFF00; color: #000; text-decoration: none; font-weight: bold; font-size: 14px; border: 2px solid #CCFF00;">
                                    VERIFY EMAIL
                                </a>
                                <p style="margin: 30px 0 0 0; color: #666; font-size: 12px;">
                                    Or copy this link: {verification_link}
                                </p>
                                <p style="margin: 20px 0 0 0; color: #666; font-size: 12px;">
                                    This link expires in 24 hours.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 40px; border-top: 2px solid #333; background-color: #050505;">
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    © {datetime.now().year} CloudWatcher. Multi-Cloud Operations Platform.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def get_password_reset_email_html(name: str, reset_link: str) -> str:
    """Generate password reset HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #000; font-family: 'Courier New', monospace;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #000; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; border: 2px solid #333;">
                        <tr>
                            <td style="padding: 40px; border-bottom: 2px solid #333;">
                                <h1 style="margin: 0; color: #fff; font-size: 24px; font-weight: bold;">
                                    CLOUD<span style="color: #CCFF00;">WATCHER</span>
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px 0; color: #fff; font-size: 20px;">
                                    Reset Your Password
                                </h2>
                                <p style="margin: 0 0 20px 0; color: #888; font-size: 14px; line-height: 1.6;">
                                    Hi {name},<br><br>
                                    We received a request to reset your password. Click the button below to create a new password.
                                </p>
                                <a href="{reset_link}" 
                                   style="display: inline-block; padding: 15px 30px; background-color: #00FFFF; color: #000; text-decoration: none; font-weight: bold; font-size: 14px; border: 2px solid #00FFFF;">
                                    RESET PASSWORD
                                </a>
                                <p style="margin: 30px 0 0 0; color: #666; font-size: 12px;">
                                    Or copy this link: {reset_link}
                                </p>
                                <p style="margin: 20px 0 0 0; color: #666; font-size: 12px;">
                                    This link expires in 1 hour. If you didn't request this, you can ignore this email.
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 40px; border-top: 2px solid #333; background-color: #050505;">
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    © {datetime.now().year} CloudWatcher. Multi-Cloud Operations Platform.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def get_alert_notification_email_html(
    name: str, 
    alerts: List[dict],
    dashboard_link: str
) -> str:
    """Generate alert notification HTML"""
    
    # Build alerts table
    alerts_html = ""
    for alert in alerts[:10]:  # Max 10 alerts in email
        severity_color = {
            "high": "#FF3333",
            "medium": "#FF9900",
            "low": "#00FFFF"
        }.get(alert.get("severity", "low"), "#888")
        
        alerts_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #333;">
                <span style="display: inline-block; padding: 4px 8px; background-color: {severity_color}; color: {'#000' if alert.get('severity') != 'high' else '#fff'}; font-size: 10px; font-weight: bold; text-transform: uppercase;">
                    {alert.get('severity', 'N/A')}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #333; color: #fff; font-size: 13px;">
                {alert.get('title', 'Unknown Alert')}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #333; color: #888; font-size: 12px; text-transform: uppercase;">
                {alert.get('category', 'N/A')}
            </td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #000; font-family: 'Courier New', monospace;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #000; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; border: 2px solid #333;">
                        <tr>
                            <td style="padding: 40px; border-bottom: 2px solid #333;">
                                <h1 style="margin: 0; color: #fff; font-size: 24px; font-weight: bold;">
                                    CLOUD<span style="color: #CCFF00;">WATCHER</span>
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 10px 0; color: #fff; font-size: 20px;">
                                    ⚠️ New Recommendations Detected
                                </h2>
                                <p style="margin: 0 0 30px 0; color: #888; font-size: 14px;">
                                    Hi {name}, we found {len(alerts)} new recommendation(s) for your infrastructure.
                                </p>
                                
                                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #333;">
                                    <tr style="background-color: #1a1a1a;">
                                        <th style="padding: 12px; text-align: left; color: #888; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #333;">Severity</th>
                                        <th style="padding: 12px; text-align: left; color: #888; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #333;">Issue</th>
                                        <th style="padding: 12px; text-align: left; color: #888; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #333;">Category</th>
                                    </tr>
                                    {alerts_html}
                                </table>
                                
                                <div style="margin-top: 30px;">
                                    <a href="{dashboard_link}" 
                                       style="display: inline-block; padding: 15px 30px; background-color: #CCFF00; color: #000; text-decoration: none; font-weight: bold; font-size: 14px; border: 2px solid #CCFF00;">
                                        VIEW ALL RECOMMENDATIONS
                                    </a>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 40px; border-top: 2px solid #333; background-color: #050505;">
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    © {datetime.now().year} CloudWatcher. Multi-Cloud Operations Platform.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def get_sync_complete_email_html(
    name: str,
    accounts_synced: int,
    instances_found: int,
    new_recommendations: int,
    dashboard_link: str
) -> str:
    """Generate sync complete notification HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #000; font-family: 'Courier New', monospace;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #000; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; border: 2px solid #333;">
                        <tr>
                            <td style="padding: 40px; border-bottom: 2px solid #333;">
                                <h1 style="margin: 0; color: #fff; font-size: 24px; font-weight: bold;">
                                    CLOUD<span style="color: #CCFF00;">WATCHER</span>
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 10px 0; color: #fff; font-size: 20px;">
                                    ✅ Sync Complete
                                </h2>
                                <p style="margin: 0 0 30px 0; color: #888; font-size: 14px;">
                                    Hi {name}, your scheduled inventory sync has completed.
                                </p>
                                
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td width="33%" style="padding: 20px; text-align: center; border: 1px solid #333; background-color: #1a1a1a;">
                                            <div style="color: #CCFF00; font-size: 32px; font-weight: bold;">{accounts_synced}</div>
                                            <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-top: 5px;">Accounts Synced</div>
                                        </td>
                                        <td width="33%" style="padding: 20px; text-align: center; border: 1px solid #333; background-color: #1a1a1a;">
                                            <div style="color: #00FFFF; font-size: 32px; font-weight: bold;">{instances_found}</div>
                                            <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-top: 5px;">Instances Found</div>
                                        </td>
                                        <td width="33%" style="padding: 20px; text-align: center; border: 1px solid #333; background-color: #1a1a1a;">
                                            <div style="color: #FF9900; font-size: 32px; font-weight: bold;">{new_recommendations}</div>
                                            <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-top: 5px;">New Alerts</div>
                                        </td>
                                    </tr>
                                </table>
                                
                                <div style="margin-top: 30px;">
                                    <a href="{dashboard_link}" 
                                       style="display: inline-block; padding: 15px 30px; background-color: #CCFF00; color: #000; text-decoration: none; font-weight: bold; font-size: 14px; border: 2px solid #CCFF00;">
                                        VIEW DASHBOARD
                                    </a>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 20px 40px; border-top: 2px solid #333; background-color: #050505;">
                                <p style="margin: 0; color: #666; font-size: 11px;">
                                    © {datetime.now().year} CloudWatcher. Multi-Cloud Operations Platform.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


# ==================== EMAIL SERVICE ====================

class EmailService:
    def __init__(self):
        self.enabled = bool(RESEND_API_KEY)
        if not self.enabled:
            logger.warning("Email service disabled: RESEND_API_KEY not set")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str
    ) -> dict:
        """Send an email using Resend"""
        if not self.enabled:
            logger.info(f"Email would be sent to {to}: {subject}")
            return {"success": True, "message": "Email disabled (no API key)", "mock": True}
        
        try:
            params = {
                "from": SENDER_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html
            }
            
            # Run sync SDK in thread
            email = await asyncio.to_thread(resend.Emails.send, params)
            
            logger.info(f"Email sent to {to}: {subject}")
            return {
                "success": True,
                "email_id": email.get("id"),
                "message": f"Email sent to {to}"
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send email: {str(e)}"
            }
    
    async def send_verification_email(self, to: str, name: str, token: str) -> dict:
        """Send email verification"""
        verification_link = f"{APP_URL}/verify-email?token={token}"
        html = get_verification_email_html(name, verification_link)
        return await self.send_email(
            to=to,
            subject=f"[{APP_NAME}] Verify Your Email",
            html=html
        )
    
    async def send_password_reset_email(self, to: str, name: str, token: str) -> dict:
        """Send password reset email"""
        reset_link = f"{APP_URL}/reset-password?token={token}"
        html = get_password_reset_email_html(name, reset_link)
        return await self.send_email(
            to=to,
            subject=f"[{APP_NAME}] Reset Your Password",
            html=html
        )
    
    async def send_alert_notification(
        self, 
        to: str, 
        name: str, 
        alerts: List[dict]
    ) -> dict:
        """Send alert notification email"""
        dashboard_link = f"{APP_URL}/recommendations"
        html = get_alert_notification_email_html(name, alerts, dashboard_link)
        
        high_count = sum(1 for a in alerts if a.get("severity") == "high")
        subject_prefix = "🔴" if high_count > 0 else "🟡"
        
        return await self.send_email(
            to=to,
            subject=f"{subject_prefix} [{APP_NAME}] {len(alerts)} New Recommendation(s)",
            html=html
        )
    
    async def send_sync_complete_notification(
        self,
        to: str,
        name: str,
        accounts_synced: int,
        instances_found: int,
        new_recommendations: int
    ) -> dict:
        """Send sync complete notification"""
        dashboard_link = f"{APP_URL}/"
        html = get_sync_complete_email_html(
            name, 
            accounts_synced, 
            instances_found, 
            new_recommendations,
            dashboard_link
        )
        return await self.send_email(
            to=to,
            subject=f"[{APP_NAME}] Sync Complete: {instances_found} instances found",
            html=html
        )


# Global email service instance
email_service = EmailService()
