import uuid
import datetime as dt
from sqlalchemy import (
    Column, String, Integer, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    notify_reminders = Column(Boolean, default=True)
    notify_newsletter = Column(Boolean, default=False)

    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="user", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, default=gen_uuid)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")

    steps = relationship("Step", back_populates="course", order_by="Step.order", cascade="all, delete-orphan")


class Step(Base):
    """یک گام از دوره — شامل سناریو، داده‌ی درس و تمرین برای چرخه‌ی ۴ فازی."""

    __tablename__ = "steps"

    id = Column(String, primary_key=True, default=gen_uuid)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    order = Column(Integer, nullable=False)

    tag = Column(String, default="سناریو — لحظه تصمیم")
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    prompt = Column(Text, default="چه می‌کنی؟")
    ai_system_prompt = Column(Text, default="")
    ai_socratic_prompt = Column(Text, nullable=True)

    # ── فاز ۳: درس مفهومی (Lesson Reveal) ──
    lesson_title = Column(String, nullable=True)
    lesson_summary = Column(Text, nullable=True)
    lesson_body = Column(Text, nullable=True)

    # ── فاز ۴: تمرین خرد شخصی ──
    exercise_prompt = Column(Text, nullable=True)

    course = relationship("Course", back_populates="steps")
    responses = relationship("Response", back_populates="step", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("course_id", "order", name="uq_course_step_order"),)


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    current_step_order = Column(Integer, default=1)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user = relationship("User", back_populates="progress")

    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)


class Response(Base):
    """وضعیت تعامل کاربر با یک گام — ماشین حالت ۴ فازی.

    Phases:
        1 → پاسخ اولیه ثبت شده (Scenario)
        2 → سؤال سقراطی دریافت شده / پاسخ دوم ثبت شده (Socratic Probe)
        3 → درس باز شد (Lesson Unlocked)
        4 → تمرین ارسال شد؛ گام کامل است (Completed)
    """

    __tablename__ = "responses"

    PHASE_INITIAL = 1
    PHASE_SOCRATIC = 2
    PHASE_LESSON = 3
    PHASE_COMPLETED = 4

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    step_id = Column(String, ForeignKey("steps.id"), nullable=False)

    initial_response = Column(Text, nullable=False)
    socratic_question = Column(Text, nullable=True)
    followup_response = Column(Text, nullable=True)
    # واکنشِ واقعیِ AI به followup_response — قبلاً این فیلد اصلاً وجود نداشت
    # و پاسخ دوم کاربر بدون هیچ پردازشی مستقیم به کارت درسِ ایستا می‌رفت.
    followup_reaction = Column(Text, nullable=True)
    exercise_response = Column(Text, nullable=True)
    # سنتز گرم AI روی تمرین خرد (فاز ۴) — بستن حلقه‌ی یادگیری؛ قبل از نسخه ۳
    # تمرین کاربر بدون هیچ بازخوردی در جشنِ پایان گام دفن می‌شد.
    exercise_reaction = Column(Text, nullable=True)

    current_phase = Column(Integer, default=1, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user = relationship("User", back_populates="responses")
    step = relationship("Step", back_populates="responses")

    __table_args__ = (UniqueConstraint("user_id", "step_id", name="uq_user_step_response"),)
