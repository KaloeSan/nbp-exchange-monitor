from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import List, Optional
from .models import NotificationDirection # Import the enum

# --- Data Schemas ---
class RateEntry(BaseModel):
    """Schema for a single rate entry."""
    effectiveDate: date
    mid: float

class CurrencyData(BaseModel):
    """Schema for currency data from NBP."""
    table: str
    currency: str
    code: str
    rates: List[RateEntry]

class GoldPriceEntry(BaseModel):
    """Schema for a single gold price entry."""
    data: date
    cena: float

class ExportDataBase(BaseModel):
    """Base schema for data points used in export/charting."""
    Date: date

class CurrencyExportData(ExportDataBase):
    """Schema for currency data points for export/charting."""
    Rate: float
    Currency: str

class GoldExportData(ExportDataBase):
    """Schema for gold data points for export/charting."""
    Price: float # Match original naming for consistency

# --- Notification Schemas ---

class NotificationBase(BaseModel):
    """Base schema for notification data."""
    currency: str = Field(..., min_length=3, max_length=3, pattern=r'^[A-Z]{3}$')
    threshold: float = Field(..., gt=0)
    email: EmailStr
    direction: NotificationDirection # Use the enum

    @field_validator('currency')
    def currency_uppercase(cls, v):
        return v.upper()

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""
    pass # No extra fields needed for creation

class NotificationRead(NotificationBase):
    """Schema for reading notification data (includes ID)."""
    id: int

    class Config:
        from_attributes = True # Renamed from orm_mode in Pydantic v2

# --- API Query Parameter Schemas ---
# These aren't strictly necessary for FastAPI query params but can help with validation/docs
class DataQueryParams(BaseModel):
    start_date: date
    end_date: date
    currencies: Optional[List[str]] = None # e.g. ["EUR", "USD"]

    @field_validator('currencies')
    def currencies_uppercase(cls, v):
        if v:
            return [c.upper() for c in v]
        return v

    # Add validation: end_date >= start_date
    # Add validation: NBP date range limits (more complex)