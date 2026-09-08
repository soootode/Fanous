from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/courses", tags=["courses"])


def _progress_for(db: Session, user_id: str, course: models.Course) -> int:
    prog = (
        db.query(models.UserProgress)
        .filter_by(user_id=user_id, course_id=course.id)
        .first()
    )
    return prog.current_step_order if prog else 0


@router.get("", response_model=schemas.DashboardOut)
def list_courses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    courses = db.query(models.Course).all()
    out = []
    continue_course = None

    for c in courses:
        step_order = _progress_for(db, current_user.id, c)
        item = schemas.CourseWithProgressOut(
            id=c.id,
            slug=c.slug,
            title=c.title,
            description=c.description,
            total_steps=len(c.steps),
            current_step_order=step_order,
        )
        out.append(item)
        if 0 < step_order < len(c.steps):
            if continue_course is None:
                continue_course = item

    return schemas.DashboardOut(continue_course=continue_course, courses=out)


@router.get("/{slug}/steps/{order}", response_model=schemas.StepDetailOut)
def get_step(
    slug: str,
    order: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """جزئیات کامل گام + وضعیت ۴ فازی کاربر (برای ازسرگیری)."""
    course = db.query(models.Course).filter(models.Course.slug == slug).first()
    if not course:
        raise HTTPException(404, "دوره پیدا نشد.")

    step = next((s for s in course.steps if s.order == order), None)
    if not step:
        raise HTTPException(404, "این گام وجود نداره.")

    # اعتبارسنجی پیشرفت — همان قاعده‌ی مشترک بدون off-by-one
    progress = (
        db.query(models.UserProgress)
        .filter_by(user_id=current_user.id, course_id=course.id)
        .first()
    )
    current_progress = progress.current_step_order if progress else 0
    if order > 1 and order > current_progress + 1:
        raise HTTPException(
            403,
            f"هنوز به گام {order} نرسیدی. اول گام {current_progress + 1} را کامل کن."
        )

    existing = (
        db.query(models.Response)
        .filter_by(user_id=current_user.id, step_id=step.id)
        .first()
    )
    user_state = (
        schemas.ResponseStateOut(
            response_id=existing.id,
            current_phase=existing.current_phase,
            initial_response=existing.initial_response,
            socratic_question=existing.socratic_question,
            followup_response=existing.followup_response,
            followup_reaction=existing.followup_reaction,
            exercise_response=existing.exercise_response,
            is_completed=existing.is_completed,
        ) if existing else None
    )

    detail = schemas.StepDetailOut(
        id=step.id,
        order=step.order,
        tag=step.tag,
        title=step.title,
        body=step.body,
        prompt=step.prompt,
        lesson_title=step.lesson_title,
        lesson_summary=step.lesson_summary,
        lesson_body=step.lesson_body,
        exercise_prompt=step.exercise_prompt,
        user_response=user_state,
    )
    return detail
