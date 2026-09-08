from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/name", response_model=schemas.UserOut)
def update_name(
    payload: schemas.UpdateNameRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    current_user.name = payload.name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/email", response_model=schemas.UserOut)
def update_email(
    payload: schemas.UpdateEmailRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    exists = (
        db.query(models.User)
        .filter(models.User.email == payload.email, models.User.id != current_user.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="این ایمیل قبلاً برای یه حساب دیگه استفاده شده.")

    current_user.email = payload.email
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=204)
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if not security.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="رمز فعلی اشتباهه.")

    current_user.hashed_password = security.hash_password(payload.new_password)
    db.commit()


@router.patch("/me/notifications", response_model=schemas.UserOut)
def update_notifications(
    payload: schemas.UpdateNotificationsRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if payload.notify_reminders is not None:
        current_user.notify_reminders = payload.notify_reminders
    if payload.notify_newsletter is not None:
        current_user.notify_newsletter = payload.notify_newsletter
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=204)
def delete_account(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    db.delete(current_user)
    db.commit()
