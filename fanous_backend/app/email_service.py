"""
سرویس ارسال ایمیل — سبک، مبتنی بر smtplib استاندارد پایتون (Gmail / Brevo / Mailgun SMTP).

متغیرهای محیطی:
    SMTP_HOST       آدرس سرور SMTP (مثلاً smtp.gmail.com یا smtp-relay.brevo.com)
    SMTP_PORT       پورت (پیش‌فرض 587 — STARTTLS)
    SMTP_USER       نام کاربری
    SMTP_PASSWORD   رمز/کلید API
    EMAILS_FROM     فرستنده (پیش‌فرض noreply@fanous.dev)

Fallback امن:
    اگر اعتبارنامه تنظیم نشده باشد، ایمیل «ارسال» نمی‌شود؛ فقط موضوع، گیرنده و
    بدنه در لاگ چاپ می‌شود تا تست لوکال و CI هرگز نشکند.
"""
import logging
import os
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

logger = logging.getLogger(__name__)

SMTP_HOST: Optional[str] = os.environ.get("SMTP_HOST")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER: Optional[str] = os.environ.get("SMTP_USER")
SMTP_PASSWORD: Optional[str] = os.environ.get("SMTP_PASSWORD")
EMAILS_FROM: str = os.environ.get("EMAILS_FROM", "noreply@fanous.dev")

_SMTP_TIMEOUT_SECONDS = 15


def is_configured() -> bool:
    """آیا اعتبارنامه‌ی SMTP کامل تنظیم شده؟"""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """ایمیل HTML می‌فرستد. در نبودِ تنظیمات، به لاگ fallback می‌کند.

    Returns:
        True اگر واقعاً ارسال شد؛ False اگر به لاگ افتاد یا ارسال شکست خورد.
        callerها باید به مقدار بازگشتی برای UX تکیه نکنند (fire-and-forget).
    """
    if not to_email or not subject or not html_body:
        logger.warning("send_email skipped: missing recipient/subject/body.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = formataddr(("فانوس 🏮", EMAILS_FROM))
    message["To"] = to_email
    message.attach(MIMEText(html_body, "html", "utf-8"))

    if not is_configured():
        logger.info(
            "[EMAIL FALLBACK - SMTP تنظیم نشده]\n"
            "To: %s\nSubject: %s\n%s",
            to_email,
            subject,
            "-" * 60,
        )
        logger.debug("Email body:\n%s", html_body)
        return False

    try:
        with smtplib.SMTP(SMTP_HOST or "", SMTP_PORT, timeout=_SMTP_TIMEOUT_SECONDS) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER or "", SMTP_PASSWORD or "")
            server.sendmail(EMAILS_FROM, [to_email], message.as_string())
        logger.info("Email sent to %s | subject=%s", to_email, subject)
        return True
    except Exception:  # noqa: BLE001 — خطای شبکه/اعتبارنامه نباید درخواست اصلی را بیندازد
        logger.exception("Failed to send email to %s", to_email)
        return False


# ─────────────────────────────────────────────────────────────
# قالب مشترک — راست‌به‌چپ، ریسپانسیو، هم‌خانواده با طراحی فانوس
# ─────────────────────────────────────────────────────────────

_LAYOUT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f0e8;font-family:'Vazirmatn',Tahoma,'Segoe UI',sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f0e8;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="max-width:520px;background-color:#fffcf4;border:1px solid rgba(200,180,140,0.5);border-radius:16px;overflow:hidden;">
          <!-- هدر زیتونی -->
          <tr>
            <td style="background:linear-gradient(150deg,#47502f,#363c22);padding:28px 28px 22px;text-align:center;">
              <div style="font-size:22px;color:#e0a458;line-height:1;">🏮</div>
              <div style="color:#f7f2e6;font-size:19px;font-weight:700;letter-spacing:0.04em;margin-top:8px;">فانوس</div>
              <div style="color:rgba(247,242,230,0.75);font-size:12.5px;margin-top:4px;">راهنمای سقراطی تفکر به فارسی</div>
            </td>
          </tr>
          <!-- بدنه -->
          <tr>
            <td style="padding:30px 28px 6px;">
              <h1 style="margin:0 0 14px;font-size:18px;font-weight:700;color:#363c22;text-align:right;">{title}</h1>
              <div style="font-size:14px;line-height:2.05;color:#5c5442;text-align:right;">{body_html}</div>
            </td>
          </tr>
          <!-- دکمه -->
          {cta_block}
          <!-- فوتر -->
          <tr>
            <td style="padding:18px 28px 26px;border-top:1px solid rgba(200,180,140,0.35);">
              <p style="margin:0;font-size:11.5px;color:#9a8e7a;line-height:1.9;text-align:right;">
                این ایمیل در پاسخ به فعالیتی که خودت انجام دادی فرستاده شده.
                اگه تو این درخواست رو ندادی، این ایمیل رو نادیده بگیر — هیچ تغییری روی حسابت اعمال نمی‌شود.
              </p>
              <p style="margin:10px 0 0;font-size:11px;color:#9a8e7a;text-align:center;">© فانوس — با فانوس، فکرت روشن‌تره.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

_CTA_TEMPLATE = """\
<tr>
  <td align="center" style="padding:18px 28px 10px;">
    <a href="{cta_url}"
       style="display:inline-block;background-color:#e0a458;color:#3a2f1d;
              font-size:15px;font-weight:700;text-decoration:none;
              padding:14px 38px;border-radius:10px;letter-spacing:0.02em;">{cta_text}</a>
    <p dir="ltr" style="margin:14px auto 0;font-size:11px;color:#9a8e7a;word-break:break-all;max-width:440px;">{cta_url}</p>
  </td>
</tr>
"""


def _render_layout(title: str, body_html: str, cta_text: str = "", cta_url: str = "") -> str:
    cta_block = ""
    if cta_text and cta_url:
        cta_block = _CTA_TEMPLATE.format(cta_text=cta_text, cta_url=cta_url)
    return _LAYOUT_TEMPLATE.format(title=title, body_html=body_html, cta_block=cta_block)


# ─────────────────────────────────────────────────────────────
# ایمیل بازیابی رمز عبور
# ─────────────────────────────────────────────────────────────

def build_password_reset_email(reset_url: str) -> tuple[str, str]:
    subject = "بازیابی رمز عبور فانوس 🏮"
    body_html = (
        "<p>سلام!</p>"
        "<p>درخواست بازیابی رمز عبور برای حسابت در فانوس ثبت شده."
        " با کلیک روی دکمه‌ی پایین می‌تونی یه رمز جدید انتخاب کنی:</p>"
        "<p style=\"font-size:12.5px;color:#9a8e7a;\">⏳ این لینک فقط ۳۰ دقیقه اعتبار داره و فقط یک بار قابل استفاده است.</p>"
    )
    return subject, _render_layout(
        title="بازیابی رمز عبور",
        body_html=body_html,
        cta_text="انتخاب رمز عبور جدید",
        cta_url=reset_url,
    )


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    subject, html = build_password_reset_email(reset_url)
    return send_email(to_email, subject, html)


# ─────────────────────────────────────────────────────────────
# ایمیل خوش‌آمدگویی (پس از ثبت‌نام — اختیاری/background)
# ─────────────────────────────────────────────────────────────

def build_welcome_email(name: str, app_url: str = "https://fanous-frontend.vercel.app") -> tuple[str, str]:
    display_name = (name or "").strip() or "دوست من"
    subject = "به فانوس خوش اومدی 🏮"
    body_html = (
        f"<p>سلام {display_name}!</p>"
        "<p>حسابت ساخته شد — سفر فکر کردن عمیق‌تر شروع شد. 🎉</p>"
        "<p>فانوس نصیحت نمی‌کنه؛ با سناریوهای واقعی و پرسش‌های سقراطی کاری می‌کنه"
        " خودت به جواب برسی. اولین گام منتظرته:</p>"
    )
    return subject, _render_layout(
        title="سفرت رو روشن کن",
        body_html=body_html,
        cta_text="شروع اولین سناریو",
        cta_url=f"{app_url.rstrip('/')}/dashboard.html",
    )


def send_welcome_email(to_email: str, name: str) -> bool:
    subject, html = build_welcome_email(name)
    return send_email(to_email, subject, html)
