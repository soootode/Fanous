"""
تست end-to-end فانوس — چرخه‌ی کامل ۴ فازی یک گام.

اجرای:
    # بک‌اند باید روشن باشد
    python test_e2e.py

    # یا با آدرس production:
    BASE_URL=https://fanous-backend.vercel.app python test_e2e.py
"""
import os
import sys

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_EMAIL = "test_e2e@fanous.dev"
TEST_PASS = "test_password_123"
TEST_NAME = "تست خودکار"


def log(step: str, ok: bool, detail: str = ""):
    icon = "✅" if ok else "❌"
    print(f"{icon}  {step}", f"— {detail}" if detail else "")
    if not ok:
        sys.exit(1)


def main():
    print(f"\n🏮 فانوس E2E Test (چرخه‌ی ۴ فازی) — {BASE_URL}\n")
    client = httpx.Client(base_url=BASE_URL, timeout=60)

    # ─── ۱. Health check ───────────────────────────────────────────
    r = client.get("/health")
    log("Health check", r.status_code == 200, r.text[:80])

    # ─── ۲. Signup / Login ─────────────────────────────────────────
    r = client.post("/auth/signup", json={
        "name": TEST_NAME,
        "email": TEST_EMAIL,
        "password": TEST_PASS,
    })
    if r.status_code == 409:
        log("Signup (already exists)", True, "ادامه با login")
    else:
        log("Signup", r.status_code == 201, f"status={r.status_code}")

    r = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASS})
    log("Login", r.status_code == 200, f"status={r.status_code}")
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # ─── ۳. Courses & Step ─────────────────────────────────────────
    r = client.get("/courses", headers=headers)
    courses = r.json().get("courses", [])
    slug = courses[0]["slug"]
    log("GET /courses", r.status_code == 200, f"slug={slug}")

    r = client.get(f"/courses/{slug}/steps/1", headers=headers)
    step = r.json()
    step_id = step["id"]
    log(
        "GET step detail",
        r.status_code == 200,
        f"lesson={bool(step.get('lesson_title'))}, exercise={bool(step.get('exercise_prompt'))}",
    )

    # ─── ۴. فاز ۱ → ۲ — پاسخ اولیه و سؤال سقراطی ──────────────────
    r = client.post(
        f"/steps/{step_id}/submit-initial",
        headers=headers,
        json={"text": "این یک پاسخ تست است برای بررسی عملکرد سیستم."},
    )
    ok = r.status_code == 200
    data = r.json() if ok else {}
    log("POST submit-initial", ok, f"phase={data.get('next_phase')}")
    question = data.get("socratic_question", "")
    response_id = data.get("response_id", "")
    log("Socratic question received", bool(question), question[:60] + "...")
    log("Response id returned", bool(response_id))

    # Idempotency — ارسال مجدد نباید خطا بدهد
    r = client.post(
        f"/steps/{step_id}/submit-initial",
        headers=headers,
        json={"text": "پاسخ آپدیت شده."},
    )
    log("submit-initial idempotent", r.status_code == 200, f"status={r.status_code}")

    # ─── ۵. فاز ۲ → ۳ — پاسخ دوم و باز شدن درس ────────────────────
    r = client.post(
        f"/steps/{step_id}/submit-followup",
        headers=headers,
        json={"text": "پاسخ دوم من روی پرسش سقراطی."},
    )
    ok = r.status_code == 200
    lesson = r.json() if ok else {}
    log(
        "POST submit-followup",
        ok,
        f"lesson={lesson.get('lesson_title', '')[:30]}, phase={lesson.get('next_phase')}",
    )

    # ─── ۶. فاز ۳ → ۴ — تمرین خرد و تکمیل گام ─────────────────────
    r = client.post(
        f"/steps/{step_id}/submit-exercise",
        headers=headers,
        json={"text": "تمرین خرد من برای همین هفته."},
    )
    ok = r.status_code == 200
    result = r.json() if ok else {}
    log(
        "POST submit-exercise",
        ok and result.get("is_completed") is True,
        f"completed={result.get('is_completed')}, next={result.get('next_step_order')}",
    )

    # ─── ۷. پیشرفت در داشبورد ──────────────────────────────────────
    r = client.get("/courses", headers=headers)
    updated = next((c for c in r.json().get("courses", []) if c["slug"] == slug), {})
    progress = updated.get("current_step_order", 0)
    log("Progress persisted in DB", progress >= 2, f"current_step_order={progress}")

    # ─── ۸. ازسرگیری گام تکمیل‌شده ─────────────────────────────────
    r = client.get(f"/courses/{slug}/steps/1", headers=headers)
    user_resp = r.json().get("user_response")
    log(
        "Resume state returned",
        bool(user_resp) and user_resp.get("current_phase") == 4,
        f"phase={user_resp.get('current_phase') if user_resp else None}",
    )

    print("\n🎉 همه تست‌ها پاس شدند!\n")
    client.close()


if __name__ == "__main__":
    main()
