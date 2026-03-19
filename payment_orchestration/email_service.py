import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending transactional emails including delivery notifications,
    error notifications, and license expiration warnings."""
    
    def __init__(self, smtp_host=None, smtp_port=None, from_email=None, from_password=None):
        """Initialize email service with SMTP configuration.
        
        Args:
            smtp_host: SMTP server hostname (defaults to env var SMTP_HOST)
            smtp_port: SMTP server port (defaults to env var SMTP_PORT or 587)
            from_email: Sender email address (defaults to env var SMTP_USER)
            from_password: SMTP password (defaults to env var SMTP_PASSWORD)
        """
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.from_email = from_email or os.getenv('SMTP_USER', '')
        self.from_password = from_password or os.getenv('SMTP_PASSWORD', '')
    
    def send_email(self, recipient, subject, html_body):
        """Send an email with HTML content.
        
        Args:
            recipient: Recipient email address
            subject: Email subject line
            html_body: HTML content of the email
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = recipient
            
            msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.from_password)
                server.sendmail(self.from_email, [recipient], msg.as_string())
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False

    async def send_delivery_email(self, to_email, customer_name, plan_name, license_key, download_url):
        """Send product delivery email with license key and download link.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            plan_name: Name of the purchased plan
            license_key: Generated license key
            download_url: Product download URL
            
        Returns:
            bool: True if email sent successfully
        """
        subject = f"🎉 Your {plan_name} License is Ready!"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .license-box {{ background: #f8f9fa; border: 2px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 8px; font-family: monospace; font-size: 16px; text-align: center; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; margin: 20px 0; }}
                .footer {{ background: #2d3748; color: white; padding: 20px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome, {customer_name}!</h1>
                    <p>Your {plan_name} license is ready to use.</p>
                </div>
                <div class="content">
                    <h2>📋 Your License Key</h2>
                    <div class="license-box">{license_key}</div>
                    
                    <h2>📥 Download Your Product</h2>
                    <p>Click the button below to download your installer:</p>
                    <a href="{download_url}" class="button">Download Now</a>
                    <p><small>This download link expires in 7 days.</small></p>
                    
                    <h2>🚀 Getting Started</h2>
                    <ol>
                        <li>Download the installer using the button above</li>
                        <li>Run the installer on your machine</li>
                        <li>Enter your license key when prompted</li>
                        <li>Start using your new AI-powered tool!</li>
                    </ol>
                    
                    <h2>📞 Need Help?</h2>
                    <p>Our support team is here to help:</p>
                    <ul>
                        <li>Email: droxai25@outlook.com</li>
                        <li>Response time: Usually within 24 hours</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>&copy; 2025 DroxAI LLC. All rights reserved.</p>
                    <p>Self-hosted AI software that pays for itself.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body)
    
    async def send_error_notification(self, to_email, customer_name, order_id, error_message):
        """Send error notification email to customer.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            order_id: Order ID that failed
            error_message: Error description
            
        Returns:
            bool: True if email sent successfully
        """
        subject = f"⚠️ Issue with Your Order {order_id}"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1>Hi {customer_name},</h1>
                <p>We encountered an issue processing your order <strong>{order_id}</strong>.</p>
                <div style="background: #fee; border-left: 4px solid #f56565; padding: 15px; margin: 20px 0;">
                    <strong>Error:</strong> {error_message}
                </div>
                <p>Our team has been notified and is working on resolving this issue. You will receive an update within 24 hours.</p>
                <p>If you have any questions, please contact us at droxai25@outlook.com</p>
                <p>Order ID: {order_id}</p>
                <p>Best regards,<br>DroxAI Support Team</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body)
    
    async def send_license_expiration_warning(self, to_email, customer_name, license_key, expiration_date, days_remaining):
        """Send license expiration warning email.
        
        Args:
            to_email: Customer email address
            customer_name: Customer's name
            license_key: License key
            expiration_date: Expiration date string
            days_remaining: Days until expiration
            
        Returns:
            bool: True if email sent successfully
        """
        subject = f"⚠️ Your License Expires in {days_remaining} Days"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1>Hi {customer_name},</h1>
                <p>Your license key is set to expire soon:</p>
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                    <p><strong>License Key:</strong> {license_key}</p>
                    <p><strong>Expires:</strong> {expiration_date}</p>
                    <p><strong>Days Remaining:</strong> {days_remaining}</p>
                </div>
                <p>To continue using your product without interruption, please renew your license before it expires.</p>
                <p>Contact us at droxai25@outlook.com to renew.</p>
                <p>Best regards,<br>DroxAI Team</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_body)