from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import auth, users, courses, progress

Base.metadata.create_all(bind=engine)


def _ensure_schema() -> None:
    """مهاجرتِ سبک برای دیتابیس‌های موجود — create_all ستون‌های جدید را به جدولِ
    ساخته‌شده اضافه نمی‌کند؛ هر ستونِ ثبت‌شده در مدل Response که در دیتابیس نیست،
    با ALTER TABLE اضافه می‌شود (idempotent — همیشه می‌توان app را بالا آورد)."""
    import logging

    from sqlalchemy import inspect, text

    logger = logging.getLogger(__name__)
    try:
        inspector = inspect(engine)
        if "responses" in inspector.get_table_names():
            existing = {col["name"] for col in inspector.get_columns("responses")}
            missing = [
                col for col in models.Response.__table__.columns
                if col.name not in existing
            ]
            if not missing:
                return
            with engine.begin() as conn:
                for col in missing:
                    col_type = col.type.compile(engine.dialect)
                    conn.execute(text(
                        f"ALTER TABLE responses ADD COLUMN {col.name} {col_type}"
                    ))
                    logger.info(
                        "Migration: responses.%s (%s) added.", col.name, col_type,
                    )
    except Exception:  # noqa: BLE001 — مهاجرت نباید app را بالا نیاورَد
        logger.exception("responses schema migration check failed")

_ensure_schema()

app = FastAPI(title="فانوس API", version="0.1.0")

# ── CORS: مبداها از متغیر محیطی ALLOWED_ORIGINS (جداشده با کاما) ──
# + تمام زیردامنه‌های *.vercel.app با regex؛ جلوگیری از خطای 403/400 در preflight
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = [
        "https://fanoos-sigma.vercel.app",
        "https://fanous-frontend.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(progress.router)


@app.get("/health")
def health():
    return {"status": "فانوس روشنه 🏮"}
