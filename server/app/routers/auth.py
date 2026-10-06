import os
import hashlib
import secrets
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.security_log import SecurityLog

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & RBAC"]
)

# Secret key for token hashing
SECRET_SALT = os.getenv("EDITH_SECRET_SALT", "edith_tactical_defense_salt_2026")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{password}{SECRET_SALT}".encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


# --- Pydantic Schemas ---
class UserRegisterSchema(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "operator"  # admin, analyst, operator


class UserLoginSchema(BaseModel):
    username: str
    password: str


class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[datetime.datetime]


class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str
    user: UserResponseSchema


# --- Dependency for Current User ---
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization:
        # For seamless local development, if no token provided, return default tactical operator
        default_user = db.query(User).filter(User.username == "admin").first()
        if not default_user:
            default_user = User(
                username="admin",
                email="admin@edith.ai",
                hashed_password=hash_password("edith2026"),
                role="admin",
                full_name="EDITH Supreme Operator"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        return default_user

    token = authorization.replace("Bearer ", "").strip()
    # Simple token parse (username:timestamp:signature)
    parts = token.split(":")
    if len(parts) >= 1:
        username = parts[0]
        user = db.query(User).filter(User.username == username).first()
        if user and user.is_active:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials."
    )


@router.post("/register", response_model=UserResponseSchema)
def register_user(req: UserRegisterSchema, db: Session = Depends(get_db)):
    """تسجيل حساب مستخدم جديد وتحديد الصلاحيات (Admin, Analyst, Operator)"""
    existing_user = db.query(User).filter(
        (User.username == req.username) | (User.email == req.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="اسم المستخدم أو البريد الإلكتروني مسجل بالفعل."
        )

    new_user = User(
        username=req.username.strip(),
        email=req.email.strip().lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name or req.username,
        role=req.role.lower() if req.role in ["admin", "analyst", "operator"] else "operator"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # تسجيل في سجل الأمان
    audit = SecurityLog(
        event_type="AUTH_REGISTER",
        severity="INFO",
        actor=new_user.username,
        description=f"User {new_user.username} registered with role {new_user.role}."
    )
    db.add(audit)
    db.commit()

    return new_user


@router.post("/login", response_model=LoginResponseSchema)
def login(req: UserLoginSchema, db: Session = Depends(get_db)):
    """تسجيل الدخول وإصدار رمز الوصول المشفر"""
    user = db.query(User).filter(User.username == req.username.strip()).first()

    if not user or not verify_password(req.password, user.hashed_password):
        # تسجيل محاولة دخول فاشلة
        audit = SecurityLog(
            event_type="AUTH_FAILED",
            severity="WARNING",
            actor=req.username,
            description=f"Failed login attempt for user {req.username}."
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تم تعطيل هذا الحساب."
        )

    # تحديث وقت آخر تسجيل دخول
    user.last_login = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    token = f"{user.username}:{int(datetime.datetime.now().timestamp())}:{secrets.token_hex(16)}"

    # تسجيل دخول ناجح
    audit = SecurityLog(
        event_type="AUTH_LOGIN",
        severity="INFO",
        actor=user.username,
        description=f"User {user.username} successfully authenticated."
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": token,
        "token_type": "Bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponseSchema)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """جلب بيانات الحساب الحالي"""
    return current_user


@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """عرض قائمة المستخدمين (متاح لجميع المشغلين والمشرفين)"""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login
        }
        for u in users
    ]
