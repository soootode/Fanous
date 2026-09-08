"""چرخه‌ی ۴ فازی هر گام — سه endpoint تراکنشی برای ارسال پاسخ‌های کاربر.

Phases:
    POST /steps/{id}/submit-initial    → فاز ۱ ← ۲ (سؤال سقراطی)
    POST /steps/{id}/submit-followup   → فاز ۲ ← ۳ (باز شدن درس)
    POST /steps/{id}/submit-exercise   → فاز ۳ ← ۴ (تکمیل گام)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, ai_feedback
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/steps", tags=["progress"])

FALLBACK_SOCRATIC_QUESTION = ai_feedback.FALLBACK_QUESTION


def get_accessible_step(
    db: Session,
    current_user: models.User,
    step_id: str,
) -> models.Step:
    """گام را برمی‌گرداند و دسترسی کاربر را بدون off-by-one اعتبارسنجی می‌کند.

    قاعده: گام اول همیشه آزاد است؛ گام N فقط وقتی قابل دسترسی است که
    ``N <= current_step_order + 1`` (یعنی گام بعدیِ پیشرفت فعلی).
    """
    step = db.query(models.Step).filter(models.Step.id == step_id).first()
    if not step:
        raise HTTPException(404, "این گام وجود نداره.")

    progress = (
        db.query(models.UserProgress)
        .filter_by(user_id=current_user.id, course_id=step.course_id)
        .first()
    )
    current_progress = progress.current_step_order if progress else 0
    if step.order > 1 and step.order > current_progress + 1:
        raise HTTPException(
            403,
            f"هنوز به گام {step.order} نرسیدی. اول گام {current_progress + 1} را کامل کن.",
        )
    return step


def _get_or_create_response(
    db: Session,
    user: models.User,
    step: models.Step,
) -> models.Response:
    """رکورد پاسخ کاربر برای این گام را برمی‌گرداند (بدون ساخت در فازهای بالاتر)."""
    return (
        db.query(models.Response)
        .filter_by(user_id=user.id, step_id=step.id)
        .first()
    )


# ─────────────────────────────────────────────────────────────
# فاز ۱ → ۲ — سناریو و پاسخ اولیه، سپس سؤال سقراطی
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{step_id}/submit-initial",
    response_model=schemas.SubmitInitialResponse,
)
def submit_initial(
    step_id: str,
    payload: schemas.SubmitInitialRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """پاسخ اولیه را ثبت می‌کند، سؤال سقراطی تولید می‌کند و به فاز ۲ می‌رود."""
    step = get_accessible_step(db, current_user, step_id)

    response = _get_or_create_response(db, current_user, step)

    if response is None:
        response = models.Response(
            user_id=current_user.id,
            step_id=step.id,
            initial_response=payload.text,
            current_phase=models.Response.PHASE_INITIAL,
        )
        db.add(response)
    elif response.current_phase >= models.Response.PHASE_SOCRATIC:
        # ازسرگیری — سؤال قبلی را idempotent برگردان
        return schemas.SubmitInitialResponse(
            response_id=response.id,
            socratic_question=response.socratic_question or FALLBACK_SOCRATIC_QUESTION,
            next_phase=response.current_phase,
        )
    else:
        response.initial_response = payload.text
        response.is_completed = False

    try:
        question = ai_feedback.generate_socratic_question(
            scenario_body=step.body,
            user_response=payload.text,
            concept_hint=step.lesson_title or "",
            scenario_notes=(step.ai_socratic_prompt or step.ai_system_prompt or ""),
        )
    except RuntimeError as exc:
        logger.error("AI config error on step %s: %s", step_id, exc)
        question = FALLBACK_SOCRATIC_QUESTION
    except Exception as exc:  # noqa: BLE001
        logger.warning("Socratic question failed for step %s: %s", step_id, exc)
        question = FALLBACK_SOCRATIC_QUESTION

    response.socratic_question = question
    response.current_phase = models.Response.PHASE_SOCRATIC

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("submit-initial commit failed for step %s", step_id)
        raise HTTPException(500, "ثبت پاسخ ناموفق بود — دوباره امتحان کن.")
    db.refresh(response)

    return schemas.SubmitInitialResponse(
        response_id=response.id,
        socratic_question=question,
        next_phase=models.Response.PHASE_SOCRATIC,
    )


# ─────────────────────────────────────────────────────────────
# فاز ۲ → ۳ — پاسخ دوم، باز شدن درس و تمرین
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{step_id}/submit-followup",
    response_model=schemas.SubmitFollowupResponse,
)
def submit_followup(
    step_id: str,
    payload: schemas.SubmitFollowupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """پاسخ دوم روی سؤال سقراطی را ثبت می‌کند، AI با تاریخچه‌ی کامل گفتگو به آن
    واکنش واقعی نشان می‌دهد، و بعد داده‌ی درس (فاز ۳) آزاد می‌شود.

    قبلاً این endpoint فقط payload.text را ذخیره می‌کرد و مستقیم می‌پرید به یک
    کارتِ درسِ ایستا — یعنی پاسخِ دومِ کاربر هیچ‌وقت توسط هیچ‌چیزی خوانده نمی‌شد.
    """
    step = get_accessible_step(db, current_user, step_id)

    # اگر داده‌ی درس در YAML ثبت نشده باشد، با محتوای جایگزین گرم تجربه نمی‌شکند
    lesson_title = step.lesson_title or f"درس این گام: {step.title}"
    lesson_summary = step.lesson_summary or "خلاصه‌ی این درس به‌زودی کامل می‌شود."
    lesson_body = step.lesson_body or step.body
    exercise_prompt = step.exercise_prompt or "این مفهوم رو در یک اتفاق واقعی از زندگی خودت همین هفته پیدا کن و بنویس چه دیدی."

    response = _get_or_create_response(db, current_user, step)
    if response is None:
        raise HTTPException(409, "اول باید پاسخ اولیه رو بفرستی.")
    if response.current_phase < models.Response.PHASE_SOCRATIC:
        raise HTTPException(409, "اول باید پاسخ اولیه رو بفرستی.")

    if response.current_phase >= models.Response.PHASE_LESSON:
        # ازسرگیری — واکنش قبلی را idempotent برگردان، دوباره AI صدا نمی‌زنیم
        reaction = response.followup_reaction or ai_feedback.FALLBACK_FOLLOWUP_REACTION
    else:
        response.followup_response = payload.text

        try:
            reaction = ai_feedback.generate_followup_reaction(
                scenario_body=step.body,
                initial_response=response.initial_response,
                socratic_question=response.socratic_question or "",
                followup_response=payload.text,
                concept_hint=step.lesson_title or "",
                scenario_notes=(step.ai_socratic_prompt or step.ai_system_prompt or ""),
            )
        except RuntimeError as exc:
            logger.error("AI config error on followup for step %s: %s", step_id, exc)
            reaction = ai_feedback.FALLBACK_FOLLOWUP_REACTION
        except Exception as exc:  # noqa: BLE001
            logger.warning("Followup reaction failed for step %s: %s", step_id, exc)
            reaction = ai_feedback.FALLBACK_FOLLOWUP_REACTION

        response.followup_reaction = reaction
        response.current_phase = models.Response.PHASE_LESSON

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("submit-followup commit failed for step %s", step_id)
        raise HTTPException(500, "ثبت پاسخ ناموفق بود — دوباره امتحان کن.")

    return schemas.SubmitFollowupResponse(
        followup_reaction=reaction,
        lesson_title=lesson_title,
        lesson_summary=lesson_summary,
        lesson_body=lesson_body,
        exercise_prompt=exercise_prompt,
        next_phase=models.Response.PHASE_LESSON,
    )


# ─────────────────────────────────────────────────────────────
# فاز ۳ → ۴ — تمرین خرد و تکمیل گام
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{step_id}/submit-exercise",
    response_model=schemas.SubmitExerciseResponse,
)
def submit_exercise(
    step_id: str,
    payload: schemas.SubmitExerciseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """تمرین خرد را ثبت، گام را کامل و پیشرفت دوره را به‌روزرسانی می‌کند."""
    step = get_accessible_step(db, current_user, step_id)

    response = _get_or_create_response(db, current_user, step)
    if response is None or response.current_phase < models.Response.PHASE_LESSON:
        raise HTTPException(409, "برای ارسال تمرین، اول درس گام رو باز کن.")

    already_completed = response.is_completed
    if not already_completed:
        response.exercise_response = payload.text
        response.current_phase = models.Response.PHASE_COMPLETED
        response.is_completed = True

        # فاز ۴ — بستن حلقه: تمرین کاربر این‌بار در خلأ نمی‌ماند؛ AI آن را می‌خواند
        # و یک سنتزِ گرم برمی‌گرداند که به مفهوم درس پیوند می‌خورد.
        try:
            reaction = ai_feedback.generate_exercise_synthesis(
                scenario_body=step.body,
                lesson_title=step.lesson_title or "",
                user_exercise=payload.text,
            )
        except RuntimeError as exc:
            logger.error("AI config error on exercise for step %s: %s", step_id, exc)
            reaction = ai_feedback.FALLBACK_EXERCISE_SYNTHESIS
        except Exception as exc:  # noqa: BLE001
            logger.warning("Exercise synthesis failed for step %s: %s", step_id, exc)
            reaction = ai_feedback.FALLBACK_EXERCISE_SYNTHESIS

        response.exercise_reaction = reaction

    total_steps = len(step.course.steps)
    course_completed = step.order >= total_steps
    next_order = None if course_completed else step.order + 1

    progress = (
        db.query(models.UserProgress)
        .filter_by(user_id=current_user.id, course_id=step.course_id)
        .first()
    )
    if not progress:
        progress = models.UserProgress(
            user_id=current_user.id,
            course_id=step.course_id,
            current_step_order=0,
        )
        db.add(progress)

    # فقط اگر پیشرفت واقعاً جلوتر رفته، آپدیت کن
    target_order = step.order if course_completed else step.order + 1
    if target_order > progress.current_step_order:
        progress.current_step_order = target_order

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("submit-exercise commit failed for step %s", step_id)
        raise HTTPException(500, "ثبت تمرین ناموفق بود — دوباره امتحان کن.")

    return schemas.SubmitExerciseResponse(
        is_completed=True,
        exercise_reaction=response.exercise_reaction,
        next_step_order=next_order,
        course_completed=course_completed,
    )
