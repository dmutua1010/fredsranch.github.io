import os, hashlib, hmac, secrets, time
import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")

def hash_pw(pw: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${h}"

def verify_pw(pw: str, stored: str) -> bool:
    salt, h = stored.split("$")
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 200_000).hex(), h)

def make_token(user: User) -> str:
    return jwt.encode({"sub": str(user.id), "exp": int(time.time()) + 8 * 3600}, SECRET, algorithm="HS256")

def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    try:
        data = jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])
        user = db.get(User, int(data["sub"]))
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    if not user:
        raise HTTPException(401, "Unknown user")
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user
