# 🏮 فانوس (Fanous)

### پلتفرم آموزش تعاملی تفکر نقاد و مهارت‌های شناختی با هوش مصنوعی سقراطی

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20(Supabase)-336791?style=flat&logo=postgresql)](https://supabase.com)
[![Gemini AI](https://img.shields.io/badge/AI%20Engine-Google%20Gemini-8E75B2?style=flat&logo=google)](https://ai.google.dev)
[![Vite](https://img.shields.io/badge/Frontend-Vite%20MPA-646CFF?style=flat&logo=vite)](https://vitejs.dev)

> **«فانوس قرار نیست به جای تو فکر کند؛ قرار است کمک کند بهتر فکر کنی.»**

[🌐 مشاهده دموی زنده پلتفرم](https://fanoos-sigma.vercel.app)

---

## 🎯 فانوس چه مشکلی را حل می‌کند؟

بخش زیادی از آموزش سنتی به انتقال یک‌طرفه‌ی اطلاعات محدود می‌شود:  
`یاد بگیر → حفظ کن → امتحان بده`

اما مهارت‌های نرم و تفکر انتقادی با حفظیات شکل نمی‌گیرند. خواندن تعریف «مغالطه» با توانایی شناسایی آن هنگام تصمیم‌گیری‌های حساس شغلی، مالی یا عاطفی دو چیز کاملاً متفاوت است.

**فانوس تلاش می‌کند فاصله‌ی میان «دانستن یک مفهوم» و «توانایی استفاده از آن در عمل» را به صفر برساند.**

---

## 🔄 چرخه‌ی یادگیری ۴ مرحله‌ای فانوس

در فانوس، یادگیری از یک فرمول تکراری یا چت‌بات نصیحت‌گر شروع نمی‌شود؛ بلکه از یک **دوراهی پرتنش واقعی** آغاز می‌شود:

```text
[۱. سناریوی داستانی و پرتنش] 
       ↓ (پاسخ اولیه‌ی کاربر بر اساس شهود)
[۲. چالش سقراطی هوش مصنوعی] 
       ↓ (پاسخ دوم کاربر به زاویه‌ی پنهان)
[۳. گشایش درس مفهومی (لحظه Aha!)] 
       ↓ (پرده‌برداری از نام علمی مغالطه/مدل ذهنی)
[۴. تمرین خرد و بازخورد هوشمند] 
       ↓ (تثبیت مهارت در تصمیمات واقعی زندگی)
[تکمیل گام و روشن شدن فانوس 🏮]
در این فرایند، هوش مصنوعی پاسخ آماده نمی‌دهد؛ بلکه با طرح پرسش‌های سقراطی هدفمند، کاربر را با فرضیات پنهان و تعصبات ذهنی‌اش روبه‌رو می‌کند.

---

## 📚 دوره‌ها و سرفصل‌های آموزشی

پلتفرم در حال حاضر شامل **۳ دوره جامع و ۲۷ سناریوی تعاملی** است:

* **🧠 تفکر منطقی (۱۰ گام):** پایه استدلال درست، مغالطه هزینه هدررفته (Sunk Cost)، تعمیم شتاب‌زده، حمله شخصی، دوراهی کاذب و تفکر احتمالاتی.
* **🔍 تفکر نقاد — مسیر شغلی (۹ گام):** انگیزه‌ی فرستنده، کشف نفع پنهان (Cui bono)، سوگیری منبع، تضاد منافع، و شکستن حباب اطلاعاتی.
* **🌐 تفکر سیستمی (۸ گام):** مدل کوه‌یخ (Iceberg)، حلقه‌های بازخورد تقویتی/تعدیلی، تاخیرها، انتقال بار، و نقاط اهرمی در مسائل پیچیده.

---

## 🛠 فناوری‌های استفاده‌شده (Tech Stack)

* **Backend:** Python 3.12, FastAPI (Async & Serverless Architecture)
* **Database & ORM:** PostgreSQL (Supabase Cloud), SQLAlchemy 2.0
* **AI Engine:** Google Gemini API (`google-genai` SDK) with custom Socratic prompt orchestration
* **Frontend:** Vite Multi-Page Application (Vanilla JavaScript, Semantic HTML5, Custom Paper-Themed CSS Design System)
* **Auth & Security:** JWT Token Authentication, Scoped Password Reset Tokens, Strict CORS
* **Deployment:** Vercel (Serverless Backend & Frontend), Supabase (Transaction Pooler)

---

## 🚀 راهنمای نصب و اجرای محلی (Local Setup)

### ۱. راه‌اندازی بک‌اند:
```bash
cd fanous_backend
python -m venv venv

# در ویندوز:
venv\Scripts\activate
# در لینوکس/مک:
# source venv/bin/activate

pip install -r requirements.txt

# تنظیم متغیرهای محیطی در فایل .env
# DATABASE_URL=sqlite:///./fanous.db
# GEMINI_API_KEY=your_gemini_api_key
# FANOUS_SECRET_KEY=your_secret_key

# ایمپورت سناریوها در دیتابیس
python import_scenarios.py

# اجرای سرور
uvicorn main:app --reload --port 8000
