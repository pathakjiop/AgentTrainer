import uuid
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer = HTTPBearer()

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try:
        user_id_str = decode_token(credentials.credentials)
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
        
    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
