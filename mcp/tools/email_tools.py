"""
Email Tools - Send emails via SMTP
Requires user to configure SMTP credentials
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List


# SMTP Configuration - loaded from environment
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # App password for Gmail
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")


def send_email(
    to: str, 
    subject: str, 
    body: str, 
    html: bool = False,
    attachments: List[str] = None,
    cc: str = None,
    bcc: str = None
) -> Dict[str, Any]:
    """
    Send an email
    
    Requires environment variables:
    - SMTP_SERVER (default: smtp.gmail.com)
    - SMTP_PORT (default: 587)
    - SMTP_USERNAME
    - SMTP_PASSWORD (use App Password for Gmail)
    - SMTP_FROM_EMAIL
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (text or HTML)
        html: If True, body is treated as HTML
        attachments: List of file paths to attach
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return {
            "success": False, 
            "error": "Email not configured. Set SMTP_USERNAME and SMTP_PASSWORD environment variables.",
            "help": "For Gmail, use an App Password: https://myaccount.google.com/apppasswords"
        }
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM_EMAIL or SMTP_USERNAME
        msg['To'] = to
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        
        # Attach body
        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Handle attachments
        if attachments:
            for filepath in attachments:
                filepath = os.path.expanduser(filepath)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{os.path.basename(filepath)}"'
                    )
                    msg.attach(part)
        
        # Build recipient list
        recipients = [to]
        if cc:
            recipients.extend([e.strip() for e in cc.split(',')])
        if bcc:
            recipients.extend([e.strip() for e in bcc.split(',')])
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(msg['From'], recipients, msg.as_string())
        
        return {
            "success": True,
            "to": to,
            "subject": subject,
            "message": "Email sent successfully"
        }
        
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "SMTP authentication failed. Check your credentials.",
            "help": "For Gmail, make sure you're using an App Password, not your regular password."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_email_config() -> Dict[str, Any]:
    """Check if email is properly configured"""
    return {
        "configured": bool(SMTP_USERNAME and SMTP_PASSWORD),
        "smtp_server": SMTP_SERVER,
        "smtp_port": SMTP_PORT,
        "username_set": bool(SMTP_USERNAME),
        "password_set": bool(SMTP_PASSWORD),
        "from_email": SMTP_FROM_EMAIL or SMTP_USERNAME or "Not set",
        "help": "Set environment variables: SMTP_USERNAME, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, SMTP_FROM_EMAIL"
    }


def create_email_draft(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Create an email draft (doesn't send, just returns the formatted email)
    Useful for previewing before sending
    """
    return {
        "success": True,
        "draft": {
            "to": to,
            "from": SMTP_FROM_EMAIL or SMTP_USERNAME or "your-email@example.com",
            "subject": subject,
            "body": body
        },
        "message": "Draft created. Use send_email to send it."
    }
