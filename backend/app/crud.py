from sqlalchemy.orm import Session
from . import models, schemas

# --- Notification CRUD ---
def create_notification(db: Session, notification: schemas.NotificationCreate) -> models.Notification:
    """Creates a new notification record in the database."""
    db_notification = models.Notification(
        currency=notification.currency.upper(),
        threshold=notification.threshold,
        email=notification.email,
        direction=notification.direction # Store the enum member directly
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_notifications(db: Session, skip: int = 0, limit: int = 100) -> list[models.Notification]:
    """Retrieves all notification records from the database."""
    return db.query(models.Notification).offset(skip).limit(limit).all()

def get_notification_by_email_and_details(db: Session, notification: schemas.NotificationCreate) -> models.Notification | None:
    """Checks if an identical notification already exists."""
    return db.query(models.Notification).filter(
        models.Notification.email == notification.email,
        models.Notification.currency == notification.currency.upper(),
        models.Notification.threshold == notification.threshold,
        models.Notification.direction == notification.direction
    ).first()

# Add functions like get_notification(db: Session, notification_id: int)
# and delete_notification(db: Session, notification_id: int) if needed