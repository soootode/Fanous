from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    notify_reminders: bool
    notify_newsletter: bool

    class Config:
        from_attributes = True


class UpdateNameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class UpdateEmailRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ─────────────────────────────────────────────────────────────
# بازیابی رمز عبور
# ─────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=4096)
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    message: str


class UpdateNotificationsRequest(BaseModel):
    notify_reminders: Optional[bool] = None
    notify_newsletter: Optional[bool] = None


class StepOut(BaseModel):
    id: str
    order: int
    tag: str
    title: str
    body: str
    prompt: str

    class Config:
        from_attributes = True


class ResponseStateOut(BaseModel):
    """عکس لحظه‌ای از وضعیت ۴ فازی کاربر روی یک گام."""

    response_id: str
    current_phase: int
    initial_response: str
    socratic_question: Optional[str] = None
    followup_response: Optional[str] = None
    followup_reaction: Optional[str] = None
    exercise_response: Optional[str] = None
    exercise_reaction: Optional[str] = None
    is_completed: bool

    class Config:
        from_attributes = True


class StepDetailOut(StepOut):
    """جزئیات کامل گام + وضعیت فعلی کاربر (برای ازسرگیری چرخه‌ی ۴ فازی)."""

    lesson_title: Optional[str] = None
    lesson_summary: Optional[str] = None
    lesson_body: Optional[str] = None
    exercise_prompt: Optional[str] = None
    user_response: Optional[ResponseStateOut] = None


class CourseOut(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    total_steps: int

    class Config:
        from_attributes = True


class CourseWithProgressOut(CourseOut):
    current_step_order: int


# ─────────────────────────────────────────────────────────────
# چرخه‌ی ۴ فازی — Phase 1: پاسخ اولیه (Scenario)
# ─────────────────────────────────────────────────────────────

class SubmitInitialRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


class SubmitInitialResponse(BaseModel):
    response_id: str
    socratic_question: str
    next_phase: int


# ─────────────────────────────────────────────────────────────
# Phase 2: پاسخ دوم (Socratic Probe)
# ─────────────────────────────────────────────────────────────

class SubmitFollowupRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


class SubmitFollowupResponse(BaseModel):
    followup_reaction: str
    lesson_title: str
    lesson_summary: str
    lesson_body: str
    exercise_prompt: str
    next_phase: int


# ─────────────────────────────────────────────────────────────
# Phase 4: تمرین خرد (Micro-Exercise) — تکمیل گام
# ─────────────────────────────────────────────────────────────

class SubmitExerciseRequest(BaseModel):
    # حداقل ۱۵ نویسه — جلوگیری از تکمیل گام با یک حرف بی‌محتوا
    text: str = Field(min_length=15, max_length=1500)


class SubmitExerciseResponse(BaseModel):
    is_completed: bool
    # سنتز گرم AI روی تمرین کاربر — بستن حلقه‌ی یادگیری در فاز ۴
    exercise_reaction: Optional[str] = None
    next_step_order: Optional[int] = None
    course_completed: bool


class DashboardOut(BaseModel):
    continue_course: Optional[CourseWithProgressOut]
    courses: List[CourseWithProgressOut]
