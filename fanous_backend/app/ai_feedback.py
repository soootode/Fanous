"""
موتور بازخورد سقراطی — Google Gemini (SDK جدید google-genai).

بازنویسی معماری (نسخه ۲): رفع دو مشکل بنیادین نسخه‌ی قبل:
  ۱. تک‌فراخوانی‌بودن: نسخه‌ی قبل فقط در فاز ۱ (submit-initial) مدل را صدا می‌زد؛
     پاسخ فاز ۲ (submit-followup) هیچ‌وقت توسط AI خوانده نمی‌شد و مستقیم به یک
     کارت درسِ ایستا می‌رفت. حالا generate_followup_reaction اضافه شده تا فاز ۲
     هم یک واکنش واقعی و مکالمه‌محور بگیرد (با تاریخچه‌ی کامل گفتگو).
  ۲. جواب‌های از‌پیش‌نوشته در YAML: پرامپت‌های قبلی شاخه‌های if/else را با متن
     فارسیِ آماده در system prompt می‌گذاشتند و مدل صرفاً همان را بازتولید می‌کرد.
     حالا یک SOCRATIC_ENGINE_SYSTEM_PROMPT ثابت و مشترک، رفتار پایه را تعیین
     می‌کند (روش الِنخوس + تشخیص شناختی پنهان با تگ <analysis>)، و هر محتوای
     مخصوصِ سناریو (از فیلد قدیمی ai_socratic_prompt) فقط به‌عنوان «یادداشتِ
     زمینه‌ای» تزریق می‌شود، نه متنِ آماده برای کپی. این یعنی این اصلاح، بدون
     نیاز به بازنویسی فایل‌های YAML، روی هر ۲۷ سناریوی موجود اعمال می‌شود.

متغیر محیطی لازم:
    GEMINI_API_KEY=...   (از aistudio.google.com/app/apikey)
"""
import os
import re
import time
import logging
from typing import Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
MAX_OUTPUT_TOKENS = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "2048"))
TEMPERATURE = 0.7
MAX_ATTEMPTS = 2
ATTEMPT_DELAY_SECONDS = 1.5


def _get_client() -> genai.Client:
    """ساخت (یا برگرداندن) کلاینت singleton ژمینای."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY تنظیم نشده. "
                "این متغیر را در Vercel Environment Variables اضافه کن."
            )
        _client = genai.Client(api_key=api_key)
    return _client


# ─────────────────────────────────────────────────────────────
# موتور سقراطی — قوانین ثابت و مشترک برای هر سه کورس
# ─────────────────────────────────────────────────────────────

SOCRATIC_ENGINE_SYSTEM_PROMPT = """\
تو «فانوس» هستی — یک پرسشگر سقراطی در سنت الِنخوس (Elenchus). کارت تأیید کردن،
دلداری‌دادن یا نصیحت اخلاقی نیست؛ کارت این است که فرضِ پنهانی را که کاربر هنوز
به خودش اعتراف نکرده، پیدا کنی و مستقیم رو کنی — با احترام، نه با تحقیر.

قوانین سفت‌وسخت:
۱. هرگز نگو پاسخ کاربر «درست» یا «غلط» است — نه در قالب مثبت («دقیقاً»، «آفرین»)
   و نه در قالب منفی. سقراطی‌بودن یعنی پرسیدن، نه داوری‌کردن.
۲. هرگز با جمله‌های نرم‌کننده و کلیشه‌ای شروع نکن: «دیدگاه جالبیه»، «کاملاً
   درکت می‌کنم»، «نگرانی‌ات منطقیه». این جمله‌ها اصطکاک فکری را از بین می‌برند —
   و همان اصطکاک، کل ارزش این تمرین است.
۳. هرگز جواب آماده یا نصیحت مستقیم نده.
۴. حساسیت‌های فرهنگی رایج در تصمیم‌های فارسی‌زبانان را بشناس و هدف بگیر: تعارف،
   آبروداری، ترس از قضاوت فامیل/دوستان، فشار مالی و تورم، مقایسه‌ی اجتماعی،
   فومو، و مغالطه‌ی هزینه‌ی هدررفته در تصمیم‌های بزرگ زندگی (شغل، مهاجرت،
   کسب‌وکار، روابط خانوادگی).
۵. لحن: صریح، گرم اما بدون نرمش بیش‌ازحد؛ معلم بالای سر نباش، ولی هم‌دستِ
   توجیهات کاربر هم نشو.
۶. طول پاسخ نهایی: حداکثر ۲ تا ۴ جمله‌ی کوتاه (تقریباً ۶۰-۸۰ کلمه). فقط فارسی.
۷. اگر در بخش «یادداشت‌های زمینه‌ای این ایستگاه» جمله‌های نمونه یا از‌پیش‌نوشته
    دیدی، فقط برای فهمِ زاویه‌ی مفهومی بخوانشان — هرگز آن‌ها را عیناً یا نزدیک به
    عین در پاسخ خودت کپی نکن. پاسخ باید از نو، و بر مبنای عبارتِ دقیقِ خودِ کاربر
    (نه یک نمونه‌ی عمومی) ساخته شود. اگر نتوانی به یک جزئیات مشخص از حرف کاربر
    ارجاع بدهی، پاسخت را دوباره بساز.
۸. همیشه پاسخت را کامل کن و هرگز جمله را ناتمام نگذار.

پیش از نوشتن پاسخ نهایی، داخل یک تگ <analysis> (که هرگز به کاربر نشان داده
نمی‌شود) این چهار سؤال را برای خودت جواب بده:
- گزاره و توجیهِ دقیقِ کاربر، با ارجاع به عبارت خودش، چیست؟
- کدام سوگیری شناختی / مغالطه / مکانیزم دفاعی زیر این توجیه پنهان است؟
- کدام ترسِ پنهان (باختن، بی‌آبرویی، تنهاماندن در تصمیم، تنبلیِ فکری) پشت آن است؟
- با کدام سؤال یا سناریوی حدی (Edge Case) می‌توان این فرض را بدون له‌کردنِ
  کاربر، در معرض آزمون گذاشت؟

بعد از تگِ analysis، فقط پاسخ نهایی را بنویس: یک جمله‌ی بازتابِ صریح از
تناقض/توجیهِ کاربر + یک سؤال یا دوراهیِ بدون راهِ فرارِ تعارفی. هیچ متنی جز
همین دو جزء، بیرون از تگ analysis نباید نوشته شود.
"""

# فاز ۱: کاربر تازه واکنش اولیه‌اش را نوشته — سؤال سقراطیِ اول ساخته می‌شود.
PHASE1_INSTRUCTION = """\
این اولین واکنش کاربر به سناریو است. بر اساس آن، یک تلنگرِ سقراطیِ اول بساز که
او را به‌جای تأیید یا رد، به سمتِ دیدن فرضِ پنهانِ خودش ببرد.
"""

# فاز ۲: کاربر به سؤال فاز ۱ پاسخ داده — این بار باید به محتوای واقعیِ همین
# پاسخِ تازه واکنش نشان داد، نه اینکه دوباره سؤال فاز ۱ را تکرار کرد.
PHASE2_INSTRUCTION = """\
این پاسخِ دومِ کاربر به تلنگرِ فاز قبل است. حتماً به چیزِ تازه‌ای که همین الان
در این پاسخ گفت واکنش نشان بده — نه به پاسخ اولش. اگر کاربر تسلیم شد و گفت
«نمی‌دانم» یا مشابهش، این را به‌عنوان یک پاسخِ معتبر و بالغانه بازتاب بده، نه
شکست. اگر یک توجیه یا فرار تازه آورد، دقیقاً همان فرار را نشانش بده.
"""

FALLBACK_QUESTION = (
    "پاسخت رو خوندم. حالا یک قدم عقب‌تر بایست: اگه مهم‌ترین پیش‌فرضی که این تصمیم "
    "رو ساخته اشتباه باشه، چی از دست می‌دی و چی به دست میاری؟"
)

FALLBACK_FOLLOWUP_REACTION = (
    "پاسخ دومت ثبت شد. برای یک لحظه، همون جمله‌ای که الان نوشتی رو بلند بخون — "
    "و از خودت بپرس: این جمله واقعاً یک دلیله، یا یک راه برای فرار از یک تصمیم سخت‌تره؟"
)

# فاز ۴ (بستن حلقه): کاربر تازه یک اقدام شخصی نوشته — اینجا مأموریت «سقراطی‌بازی»
# نیست؛ مأموریت تثبیت یادگیری است. پرامپت موتور الِنخوس اینجا لود نمی‌شود چون
# تأییدکردن را ممنوع می‌کند — سنتزِ تمرین دقیقاً جایی است که تأییدِ گرم جایز است.
EXERCISE_SYNTHESIS_SYSTEM_PROMPT = """\
تو «فانوس» هستی. مأموریت این مرحله بستن حلقه‌ی یادگیری است: کاربر تازه یک اقدام
شخصی و مشخص برای زندگی واقعی‌اش نوشته. کار تو این است که با ۱ تا ۲ جمله‌ی کوتاه،
صمیمی و گرم، او را به‌خاطر تبدیل‌کردنِ درس به یک تعهد عملی تشویق کنی و آن را به
مفهوم اصلی درس پیوند بزنی.

قوانین سفت‌وسخت:
۱. دقیقاً به جزئی از نوشته‌ی خود کاربر ارجاع بده — آفرینِ کلی («آفرین»، «عالی بود»)
   بدون اشاره به متنِ او ممنوع است.
۲. پیوند بزن: نشان بده همین اقدامِ کوچک، مفهومِ درس را از تئوری به مهارت شخصی
   تبدیل می‌کند — بدون نام‌بردنِ خشکِ اصطلاح، مگر آنکه خود کاربر به آن اشاره کرده باشد.
۳. هیچ سؤال جدیدی نپرس و هیچ نصیحتِ اضافه نکن — این آخرین پیام گام است، نه شروعِ
   گفتگوی تازه.
۴. فقط فارسی؛ حداکثر ۲ جمله‌ی کوتاه (حدود ۳۰-۵۰ کلمه). لحن: گرم، انسانی، بدون
    شعارزدگی و بدون کارت‌پستال‌بازی.
۵. همیشه پاسخت را کامل کن و هرگز جمله را ناتمام نگذار.
"""

FALLBACK_EXERCISE_SYNTHESIS = (
    "تمرینت ثبت شد. همون اقدامی که برای همین هفته نوشتی، وقتی اجراش کنی، این مفهوم "
    "از یک حرف روی کاغذ به یک مهارت واقعی تبدیل می‌شه — و این دقیقاً همون چیزیه که "
    "فانوس برایش ساخته شده."
)


# اگر مدل تگ <analysis> را کلاً جا انداخته باشد، متنِ تحلیل به‌صورت بولت‌های
# متا (مثل «- گزاره و توجیهِ دقیقِ کاربر: ...») مستقیم به کاربر می‌ریزد.
# این خطوط هرگز نباید در پاسخ نهایی دیده شوند — در هر جای خروجی حذف می‌شوند.
_ANALYSIS_META_LINE = re.compile(
    r"^\s*(?:[-*•]\s*)?(?:گزاره و توجیهِ|کدام سوگیری|کدام ترس|با کدام سؤال)"
)


def clean_socratic_output(raw_text: str) -> str:
    """حذف بلاک تحلیلی <analysis> از خروجی مدل — کاربر هرگز نباید آن را ببیند."""
    if not raw_text:
        return raw_text
    cleaned = re.sub(r"<analysis>.*?</analysis>", "", raw_text, flags=re.DOTALL | re.IGNORECASE)
    # اگر مدل تگ را نبست یا فراموش کرد، حداقل خط‌های خیلی ابتدایی متا را حذف کن.
    cleaned = re.sub(r"</?analysis>", "", cleaned, flags=re.IGNORECASE)
    cleaned = "\n".join(
        line for line in cleaned.splitlines()
        if not _ANALYSIS_META_LINE.match(line)
    )
    return cleaned.strip()


def _render_transcript(conversation: list[dict]) -> str:
    """تاریخچه‌ی گفتگو را به متن خوانا برای پرامپت تبدیل می‌کند."""
    lines = []
    for turn in conversation:
        speaker = "فانوس" if turn.get("role") == "assistant" else "کاربر"
        lines.append(f"[{speaker}]: {turn.get('text', '').strip()}")
    return "\n".join(lines)


def _build_payload(
    scenario_body: str,
    conversation: list[dict],
    phase: int,
) -> str:
    transcript = _render_transcript(conversation)
    phase_instruction = PHASE1_INSTRUCTION if phase == 1 else PHASE2_INSTRUCTION
    return (
        f"سناریو:\n{scenario_body}\n\n"
        f"گفتگو تا این لحظه:\n{transcript}\n\n"
        f"{phase_instruction}\n"
        "اول تگ <analysis> را بنویس، بعد پاسخ نهایی را طبق قوانین سیستم بساز."
    )


def _build_system(concept_hint: str, scenario_notes: str) -> str:
    system = SOCRATIC_ENGINE_SYSTEM_PROMPT
    if concept_hint:
        system += f"\n\nمفهومِ هدفِ این ایستگاه: {concept_hint}\n"
    if scenario_notes:
        system += (
            "\n--- یادداشت‌های زمینه‌ای این ایستگاه (فقط برای فهمِ زاویه، هرگز کپی نکن) ---\n"
            f"{scenario_notes}\n"
            "--- پایان یادداشت‌ها ---\n"
        )
    return system


def _call_model(system: str, prompt: str, fallback: str, log_label: str) -> str:
    client = _get_client()
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=TEMPERATURE,
                ),
            )
            raw = response.text
            cleaned = clean_socratic_output(raw) if raw else ""
            if cleaned:
                return cleaned
            last_error = ValueError("Gemini پاسخ خالی یا فقط-analysis برگرداند.")
        except Exception as exc:  # noqa: BLE001 — rate limit / timeout / network
            last_error = exc
            logger.warning(
                "%s attempt %d/%d failed: %s", log_label, attempt, MAX_ATTEMPTS, exc,
            )
        if attempt < MAX_ATTEMPTS:
            time.sleep(ATTEMPT_DELAY_SECONDS)

    logger.error("%s failed after retries: %s", log_label, last_error)
    raise RuntimeError(f"{log_label} ناموفق بود: {last_error}")


def generate_socratic_question(
    scenario_body: str,
    user_response: str,
    concept_hint: str = "",
    scenario_notes: str = "",
) -> str:
    """فاز ۱ → سؤال سقراطیِ اول را بر اساس واکنشِ خامِ کاربر تولید می‌کند.

    Args:
        scenario_body: متن روایت سناریوی گام.
        user_response: پاسخ اولیه‌ی کاربر (فاز ۱).
        concept_hint: نام مفهومِ هدف (مثلاً step.lesson_title) — اختیاری.
        scenario_notes: یادداشت‌های زمینه‌ایِ این ایستگاه (فیلد قدیمیِ
            ai_socratic_prompt/ai_system_prompt) — به‌عنوان راهنما تزریق
            می‌شود، نه متنِ آماده برای کپی.
    """
    conversation = [{"role": "user", "text": user_response}]
    system = _build_system(concept_hint, scenario_notes)
    prompt = _build_payload(scenario_body, conversation, phase=1)
    return _call_model(system, prompt, FALLBACK_QUESTION, "generate_socratic_question")


def generate_followup_reaction(
    scenario_body: str,
    initial_response: str,
    socratic_question: str,
    followup_response: str,
    concept_hint: str = "",
    scenario_notes: str = "",
) -> str:
    """فاز ۲ → واکنشِ واقعیِ AI به پاسخِ دومِ کاربر (قبلاً این فراخوانی اصلاً
    وجود نداشت و پاسخِ فاز ۲ بدون خوانده‌شدن مستقیم به کارتِ درسِ ایستا می‌رفت).
    """
    conversation = [
        {"role": "user", "text": initial_response},
        {"role": "assistant", "text": socratic_question},
        {"role": "user", "text": followup_response},
    ]
    system = _build_system(concept_hint, scenario_notes)
    prompt = _build_payload(scenario_body, conversation, phase=2)
    return _call_model(system, prompt, FALLBACK_FOLLOWUP_REACTION, "generate_followup_reaction")


def generate_exercise_synthesis(
    scenario_body: str,
    lesson_title: str,
    user_exercise: str,
) -> str:
    """فاز ۴ → سنتزِ گرم AI روی تمرین خرد کاربر (بستن حلقه‌ی یادگیری).

    قبلاً این فراخوانی اصلاً وجود نداشت: تمرینِ شخصیِ کاربر بدون هیچ بازخوردی
    مستقیم به کارت جشنِ پایان گام می‌رفت. حالا یک پیام کوتاه و گرم برمی‌گردد که
    تعهدِ کاربر را تأیید و به مفهوم درس پیوند می‌زند.
    """
    system = (
        EXERCISE_SYNTHESIS_SYSTEM_PROMPT
        + f"\n\nمفهومِ هدفِ این ایستگاه: {lesson_title or 'نامشخص'}\n"
    )
    prompt = (
        f"سناریو:\n{scenario_body}\n\n"
        f"تمرینِ خردِ کاربر (اقدامِ شخصی برای همین هفته):\n{user_exercise}\n\n"
        "یک سنتزِ گرمِ ۱ تا ۲ جمله‌ای بساز: اقدام کاربر را با ارجاع به جزئیاتِ "
        "نوشته‌اش تثبیت کن و به مفهومِ درس پیوند بزن. هیچ سؤالی نپرس."
    )
    return _call_model(
        system, prompt, FALLBACK_EXERCISE_SYNTHESIS, "generate_exercise_synthesis",
    )
