import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Dict

# Load .env file from the project root (adjust path if needed)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    """Application configuration settings."""
    PROJECT_NAME: str = "NBP Currency & Gold Analysis Platform"
    API_V1_STR: str = "/api/v1"

    # JWT Settings
    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database Configuration
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "nbp_data")
    DATABASE_URL: str = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Email Configuration (ensure these are set in your .env)
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', 587))
    EMAIL_ADDRESS: str | None = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD: str | None = os.getenv('EMAIL_PASSWORD')
    # Optional: Email sender name
    EMAILS_FROM_NAME: str | None = "NBP Currency Alert"

    # NBP API Base URL
    NBP_API_BASE_URL: str = "http://api.nbp.pl/api"

    SOAP_SERVICE_HOST: str = os.getenv('SOAP_SERVICE_HOST', '0.0.0.0')
    SOAP_SERVICE_PORT: int = int(os.getenv('SOAP_SERVICE_PORT', 8001))

    # Available Currencies (can be moved to a constants file)
    AVAILABLE_CURRENCIES: List[Dict[str, str]] = [
        {"label": "US Dollar", "value": "usd"},
        {"label": "Euro", "value": "eur"},
        {"label": "Swiss Franc", "value": "chf"},
        {"label": "British Pound", "value": "gbp"},
        {"label": "Australian Dollar", "value": "aud"},
        {"label": "Canadian Dollar", "value": "cad"},
        {"label": "Hungarian Forint", "value": "huf"},
        {"label": "Japanese Yen", "value": "jpy"},
        {"label": "Czech Koruna", "value": "czk"},
        {"label": "Danish Krone", "value": "dkk"},
        {"label": "Norwegian Krone", "value": "nok"},
        {"label": "Swedish Krona", "value": "sek"},
        {"label": "Chinese Yuan", "value": "cny"},
        {"label": "South Korean Won", "value": "krw"},
        {"label": "Bulgarian Lev", "value": "bgn"},
        {"label": "Turkish Lira", "value": "try"},
        {"label": "Israeli New Shekel", "value": "ils"},
        {"label": "New Zealand Dollar", "value": "nzd"},
        {"label": "Singapore Dollar", "value": "sgd"},
        {"label": "Romanian Leu", "value": "ron"},
        {"label": "Mexican Peso", "value": "mxn"},
        {"label": "South African Rand", "value": "zar"},
        {"label": "Brazilian Real", "value": "brl"},
        {"label": "Malaysian Ringgit", "value": "myr"},
        {"label": "Philippine Peso", "value": "php"},
        {"label": "Thai Baht", "value": "thb"},
        {"label": "Indian Rupee", "value": "inr"},
        {"label": "Indonesian Rupiah", "value": "idr"},
        {"label": "Hong Kong Dollar", "value": "hkd"},
        {"label": "Chilean Peso", "value": "clp"},
        {"label": "Ukrainian Hryvnia", "value": "uah"}
    ]

    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key_should_be_changed") # Secret key for JWT signing
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256") # Algorithm used for signing JWT tokens
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)) # Token expiration time in minutes

    class Config:
        case_sensitive = True
        env_file = '.env' # Although load_dotenv is used, this reinforces Pydantic's awareness
        extra = "ignore"


@lru_cache() # Cache the settings object
def get_settings() -> Settings:
    """Returns the application settings."""
    return Settings()

settings = get_settings()