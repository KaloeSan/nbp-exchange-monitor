from sqlalchemy import Column, Integer, String, Float, Enum as SQLEnum
from .database import Base
import enum

class NotificationDirection(enum.Enum):
    ABOVE = "above"
    BELOW = "below"

class Notification(Base):
    """Database model for storing notification alerts."""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String(3), index=True, nullable=False) # e.g., 'EUR'
    threshold = Column(Float, nullable=False)
    email = Column(String(100), index=True, nullable=False)
    direction = Column(SQLEnum(NotificationDirection), nullable=False) # 'above' or 'below'
    # You could add a 'last_triggered' timestamp or a 'is_active' flag

    def __repr__(self):
        return f"<Notification(id={self.id}, currency='{self.currency}', threshold={self.threshold}, email='{self.email}', direction='{self.direction.value}')>"

# Ensure the table is created when the application starts
# (You might prefer Alembic for production migrations)
# from .database import engine
# Base.metadata.create_all(bind=engine) # Called in main.py lifespan event instead