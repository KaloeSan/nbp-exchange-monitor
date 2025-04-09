import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import os
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from datetime import datetime
from .. import crud
from ..config import settings
from .nbp_api import get_latest_rate

logger = logging.getLogger(__name__)

def send_email_notification(notification, current_rate: float):
    """
    Sends an email alert for currency rate threshold notifications.
    Uses Gmail SMTP with App Password authentication.
    
    Args:
        notification: Notification object containing email and currency details
        current_rate: Current exchange rate for the currency
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAIL_ADDRESS}>"
        msg['To'] = notification.email
        msg['Subject'] = f"Currency Alert: {notification.currency.upper()} Rate Alert"

        # Create the email body
        body = f"""
Hello,

This is an automatic notification regarding your currency rate alert.

Currency: {notification.currency.upper()}/PLN
Current Rate: {current_rate:.4f} PLN
Your Alert Threshold: {notification.threshold:.4f} PLN
Alert Condition: Rate is {notification.direction.value} threshold

Time of Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an automated message, please do not reply.

Best regards,
{settings.PROJECT_NAME}
"""
        # Attach body to email
        msg.attach(MIMEText(body, 'plain'))

        try:
            # Setup SMTP server with SSL
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.ehlo()  # Start SMTP conversation
            server.starttls()  # Enable TLS encryption
            server.ehlo()  # Restart SMTP conversation over TLS

            # Log in to server
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            
            # Convert message to string and send
            text = msg.as_string()
            server.sendmail(settings.EMAIL_ADDRESS, notification.email, text)
            
            logger.info(f"Successfully sent alert email to {notification.email} for {notification.currency}")
            
            # Close the connection
            server.quit()
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Check your Gmail App Password and email settings.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        return False

def check_and_notify(notification, db: Session):
    """
    Checks if a notification's conditions are met and sends an email if necessary.
    
    Args:
        notification: The notification to check
        db: Database session
    
    Returns:
        bool: True if notification was sent, False otherwise
    """
    try:
        current_rate = get_latest_rate(notification.currency)
        if current_rate is None:
            logger.warning(f"Could not get current rate for {notification.currency}")
            return False

        should_notify = False
        if notification.direction.value == "above" and current_rate > notification.threshold:
            should_notify = True
            logger.info(f"Rate {current_rate} is above threshold {notification.threshold}")
        elif notification.direction.value == "below" and current_rate < notification.threshold:
            should_notify = True
            logger.info(f"Rate {current_rate} is below threshold {notification.threshold}")

        if should_notify:
            logger.info(f"Sending notification for {notification.currency} to {notification.email}")
            if send_email_notification(notification, current_rate):
                # Update last notification time
                notification.last_checked = datetime.now()
                db.commit()
                return True

        return False

    except Exception as e:
        logger.error(f"Error in check_and_notify: {str(e)}")
        return False

def check_thresholds(db: Session):
    """
    Periodic task that checks all notifications against current rates.
    """
    logger.info("Starting scheduled check of currency rate thresholds")
    try:
        notifications = crud.get_notifications(db)
        if not notifications:
            logger.info("No notifications to check")
            return

        for notification in notifications:
            try:
                check_and_notify(notification, db)
            except Exception as e:
                logger.error(f"Error checking notification {notification.id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in check_thresholds: {str(e)}")

# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True)

def start_scheduler(db_getter):
    """
    Starts the notification scheduler.
    
    Args:
        db_getter: Function that returns a database session
    """
    if not scheduler.running:
        scheduler.add_job(
            lambda: check_thresholds(next(db_getter())),
            'interval',
            minutes=15,  # Check every 15 minutes
            id='check_currency_thresholds'
        )
        scheduler.start()
        logger.info("Currency rate notification scheduler started")

def stop_scheduler():
    """Stops the notification scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Currency rate notification scheduler stopped")