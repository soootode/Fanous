import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..email_service import send_password_reset_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_BASE_URL = os.environ.get(
    "FRONTEND_BASE_URL", "https://fanous-frontend.vercel.app"
).rstrip("/")

# پیام عمومی برای جلوگیری از شمارش ایمیل‌های ثبت‌شده (user enumeration)
GENERIC_RESET_MESSAGE = "اگر این ایمیل وجود داشته باشد، لینک بازیابی ارسال شد."


@router.post("/signup", response_model=schemas.TokenResponse, status_code=201)
def signup(
    payload: schemas.SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این ایمیل قبلاً ثبت شده — می‌خوای وارد بشی؟",
        )

    user = models.User(
        name=payload.name,
        email=payload.email,
        hashed_password=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # ایمیل خوش‌آمدگویی — در پس‌زمینه؛ شکستش روی ثبت‌نام اثری ندارد
    background_tasks.add_task(send_welcome_email, user.email, user.name)

    token = security.create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ایمیل یا رمز عبور اشتباهه.",
        )

    token = security.create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user


# ─────────────────────────────────────────────────────────────
# بازیابی رمز عبور
# ─────────────────────────────────────────────────────────────


@router.post("/forgot-password", response_model=schemas.ForgotPasswordResponse)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        reset_token = security.create_password_reset_token(user.email)
        reset_url = f"{FRONTEND_BASE_URL}/reset-password.html?token={reset_token}"
        # fire-and-forget: شکست ارسال ایمیل هرگز نباید پاسخ ۲۰۰ را خراب کند
        send_password_reset_email(user.email, reset_url)

    # همیشه ۲۰۰ — حتی اگر ایمیل وجود نداشته باشد
    return schemas.ForgotPasswordResponse(message=GENERIC_RESET_MESSAGE)


@router.post("/reset-password", response_model=schemas.ResetPasswordResponse)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    email = security.decode_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لینک بازیابی نامعتبر یا منقضی شده — دوباره درخواست بده.",
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حسابی برای این لینک پیدا نشد — دوباره درخواست بده.",
        )

    user.hashed_password = security.hash_password(payload.new_password)
    db.commit()

    return schemas.ResetPasswordResponse(message="رمز عبورت عوض شد — حالا با رمز جدید وارد شو.")
