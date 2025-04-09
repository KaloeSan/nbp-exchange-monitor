from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from .config import settings
from . import schemas # Needed for user schema

# --- Configuration ---
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

# Context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme pointing to login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")

# --- Simple User Database Simulation ---
# Hashed password for 'testpassword'
hashed_password_for_testuser = pwd_context.hash("testpassword")

fake_users_db: Dict[str, Dict[str, Any]] = {
    "testuser": {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": hashed_password_for_testuser,
        "disabled": False,
    },
     "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": pwd_context.hash("adminpass"),
        "disabled": False,
    }
}

# --- Auth related Pydantic schemas ---
class Token(BaseModel):
    """ Response model for JWT Token """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """ Data model encoded in JWT """
    username: Optional[str] = None

class UserInDB(schemas.BaseModel): # BaseModel with schemas for consistency
    """ User model stored in 'database' """
    username: str
    email: Optional[EmailStr] = None
    hashed_password: str
    disabled: bool = False

    class Config:
         from_attributes = True # For Pydantic v2

# --- Auth Helper Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Verifies plaintext password with hash """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """ Generates password hash """
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[UserInDB]:
    """ Gets user from 'database' """
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        # Return as an instance of a Pydantic model for type consistency
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """ Checks user login details """
    user = get_user(username)
    if not user:
        return None # User does not exist
    if not verify_password(password, user.hashed_password):
        return None # Incorrect password
    return user # Authentication successful

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """ Creates a JWT token """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiration time from configuration
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Key and algorithm from configuration
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FastAPI dependency to get current user ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    FastAPI dependency: decodes the JWT token, validates it, and returns the user.
    Throws an HTTPException if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # Standard header for 401 errors
    )
    try:
        # Decode token using key and algorithm from configuration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub") # "sub" is the standard user id field
        if username is None:
            raise credentials_exception # If the token is missing a 'sub' field, create a TokenData object for validation
        token_data = TokenData(username=username)
    except JWTError as e:
        # Error decoding or verifying signature/expiration time
        print(f"JWT Error: {e}") # Logowanie błędu JWT może być pomocne
        raise credentials_exception

    # Get user from 'database' based on name from token
    user = get_user(token_data.username)
    if user is None:
        # If the user from the token no longer exists in the database
        raise credentials_exception
    return user # Returns a user object (UserInDB instance)

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    Dependency checking whether the user retrieved from the token is active.
    """
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user