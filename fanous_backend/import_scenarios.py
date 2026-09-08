"""
سناریوها رو از فایل‌های YAML توی پوشه‌ی scenarios/ می‌خونه و توی دیتابیس می‌ریزه.

ساختار مورد انتظار هر گام:
    - order, tag, title, body, prompt
    - ai_system_prompt (اختیاری) — پرامپت کلی دوره
    - ai_socratic_prompt (اختیاری) — پرامپت اختصاصی فاز سقراطی
    - lesson:            { concept_name, summary, body }
    - exercise:          { prompt }

اجرا:
    python import_scenarios.py
"""
import glob
from typing import Any, Dict, Optional

import yaml

from app.database import Base, engine, SessionLocal
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def _clean(value: Optional[Any]) -> Optional[str]:
    """None یا رشته‌ی خالی را None برمی‌گرداند؛ بقیه را strip شده برمی‌گرداند."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


for path in sorted(glob.glob("scenarios/*.yaml")) + sorted(glob.glob("scenarios/*.yml")):
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    slug = data["slug"]
    default_prompt = data.get("default_ai_system_prompt", "")

    course = db.query(models.Course).filter(models.Course.slug == slug).first()
    if course is None:
        course = models.Course(slug=slug, title=data["title"], description=data.get("description", ""))
        db.add(course)
        db.flush()
        print(f"+ دوره‌ی جدید: {slug}")
    else:
        course.title = data["title"]
        course.description = data.get("description", "")
        print(f"~ دوره‌ی موجود آپدیت شد: {slug}")

    for step_data in data.get("steps", []):
        order = step_data["order"]
        step = (
            db.query(models.Step)
            .filter(models.Step.course_id == course.id, models.Step.order == order)
            .first()
        )
        if step is None:
            step = models.Step(course_id=course.id, order=order)
            db.add(step)

        step.tag = step_data.get("tag", "سناریو — لحظه تصمیم")
        step.title = step_data["title"]
        step.body = step_data["body"]
        step.prompt = step_data.get("prompt", "چه می‌کنی؟")

        # پرامپت سقراطی اختصاصی گام؛ در نبودش از پرامپت عمومی گام/دوره استفاده می‌شود
        step.ai_socratic_prompt = _clean(
            step_data.get("ai_socratic_prompt")
            or step_data.get("ai_system_prompt")
            or default_prompt
        )
        if "ai_system_prompt" in step_data:
            step.ai_system_prompt = step_data.get("ai_system_prompt", "")

        # ── داده‌ی درس (فاز ۳) و تمرین (فاز ۴) — با کلیدهای انعطاف‌پذیر ──
        lesson: Dict[str, Any] = step_data.get("lesson") or {}
        lesson_exercise: Dict[str, Any] = lesson.get("exercise") or {}
        top_exercise: Dict[str, Any] = step_data.get("exercise") or {}

        step.lesson_title = _clean(lesson.get("concept_name") or lesson.get("title"))
        step.lesson_summary = _clean(lesson.get("summary"))
        step.lesson_body = _clean(lesson.get("takeaway") or lesson.get("body"))
        step.exercise_prompt = _clean(
            top_exercise.get("prompt") or lesson_exercise.get("prompt")
        )

        missing = [
            name for name, val in (
                ("lesson.concept_name|title", step.lesson_title),
                ("lesson.takeaway|body", step.lesson_body),
                ("exercise.prompt", step.exercise_prompt),
            ) if not val
        ]
        if missing:
            print(f"  ⚠️  گام {order} بدون این فیلدهاست: {', '.join(missing)}")

    db.commit()
    print(f"  {len(data.get('steps', []))} گام ثبت/آپدیت شد.")

db.close()
print("تمام.")
