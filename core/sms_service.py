import json
import logging
from urllib import error
from urllib import request as urllib_request

from django.conf import settings


logger = logging.getLogger(__name__)


def _terminal_sms_debug(message):
    print(f"[SMS DEBUG] {message}", flush=True)


def build_public_url(relative_or_absolute_url):
    if not relative_or_absolute_url:
        return ""

    url = str(relative_or_absolute_url)

    if url.startswith("http://") or url.startswith("https://"):
        return url

    base_url = getattr(settings, "APP_BASE_URL", "").strip().rstrip("/")

    if not base_url:
        return url

    if not url.startswith("/"):
        url = f"/{url}"

    return f"{base_url}{url}"


def normalize_phone_number(phone_number):
    """
    نرمال‌سازی ساده شماره موبایل برای ارسال به SMS.ir

    خروجی پیشنهادی برای SMS.ir:
    09123456789
    """

    if not phone_number:
        return ""

    phone = str(phone_number).strip()

    replacements = {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }

    for persian_digit, english_digit in replacements.items():
        phone = phone.replace(persian_digit, english_digit)

    phone = (
        phone.replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace("(", "")
        .replace(")", "")
    )

    # تبدیل +98912... به 0912...
    if phone.startswith("+98"):
        phone = f"0{phone[3:]}"

    # تبدیل 98912... به 0912...
    if phone.startswith("98") and len(phone) == 12:
        phone = f"0{phone[2:]}"

    return phone


def _parse_smsir_response(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _extract_provider_status(parsed_response):
    """
    تلاش برای استخراج status/message از پاسخ SMS.ir.

    بسته به endpoint و نسخه API ممکن است ساختار پاسخ کمی متفاوت باشد.
    """

    if not isinstance(parsed_response, dict):
        return None, ""

    provider_status = (
        parsed_response.get("status")
        or parsed_response.get("Status")
        or parsed_response.get("code")
        or parsed_response.get("Code")
    )

    provider_message = (
        parsed_response.get("message")
        or parsed_response.get("Message")
        or parsed_response.get("errorMessage")
        or parsed_response.get("ErrorMessage")
        or ""
    )

    return provider_status, provider_message


def _is_provider_success(provider_status, parsed_response):
    """
    در SMS.ir معمولاً status=1 نشانه موفقیت است.
    اما برای جلوگیری از خطای احتمالی، چند حالت رایج هم بررسی شده.
    """

    if provider_status in (1, "1", 200, "200", True):
        return True

    if not isinstance(parsed_response, dict):
        return False

    # اگر پاسخ شامل data باشد و status خطا نباشد، ممکن است پذیرفته شده باشد.
    # با این حال معیار اصلی همان status است.
    if parsed_response.get("data") and provider_status in (None, ""):
        return True

    return False


def send_sms(phone_number, message_text):
    provider = (getattr(settings, "SMS_PROVIDER", "mock") or "mock").lower()

    normalized_phone = normalize_phone_number(phone_number)

    if provider != "smsir":
        details = {
            "provider": provider,
            "mode": "mock",
            "reason": "provider_not_smsir",
            "phone": normalized_phone,
        }

        logger.info(
            "SMS debug mode=mock provider=%s phone=%s",
            provider,
            normalized_phone,
        )

        _terminal_sms_debug(
            f"mode=mock provider={provider} phone={normalized_phone}"
        )

        return True, details

    api_key = getattr(settings, "SMSIR_API_KEY", "").strip()
    line_number = str(getattr(settings, "SMSIR_LINE_NUMBER", "")).strip()

    if not api_key or not line_number:
        details = {
            "provider": provider,
            "mode": "error",
            "reason": "missing_settings",
            "has_api_key": bool(api_key),
            "has_line_number": bool(line_number),
            "phone": normalized_phone,
        }

        logger.warning(
            "SMS.ir settings are incomplete. "
            "SMSIR_API_KEY exists=%s SMSIR_LINE_NUMBER exists=%s phone=%s",
            bool(api_key),
            bool(line_number),
            normalized_phone,
        )

        _terminal_sms_debug("========== SMS.IR SETTINGS ERROR ==========")
        _terminal_sms_debug(f"phone={normalized_phone}")
        _terminal_sms_debug(f"has_api_key={bool(api_key)}")
        _terminal_sms_debug(f"has_line_number={bool(line_number)}")
        _terminal_sms_debug("===========================================")

        return False, details

    if not normalized_phone:
        details = {
            "provider": provider,
            "mode": "error",
            "reason": "empty_phone_number",
            "phone": normalized_phone,
        }

        logger.warning("SMS.ir phone number is empty.")

        _terminal_sms_debug("========== SMS.IR PHONE ERROR ==========")
        _terminal_sms_debug("phone is empty")
        _terminal_sms_debug("========================================")

        return False, details

    endpoint = getattr(
        settings,
        "SMSIR_SEND_ENDPOINT",
        "https://api.sms.ir/v1/send/bulk",
    )

    payload = {
        "lineNumber": line_number,
        "messageText": message_text,
        "mobiles": [normalized_phone],
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": api_key,
    }

    try:
        req = urllib_request.Request(
            endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        with urllib_request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed_response = _parse_smsir_response(raw)

            provider_status, provider_message = _extract_provider_status(
                parsed_response
            )

            details = {
                "provider": provider,
                "mode": "live",
                "phone": normalized_phone,
                "status_code": response.status,
                "response": raw,
                "parsed_response": parsed_response,
                "provider_status": provider_status,
                "provider_message": provider_message,
            }

            _terminal_sms_debug("========== SMS.IR RESPONSE ==========")
            _terminal_sms_debug(f"phone={normalized_phone}")
            _terminal_sms_debug(f"http_status={response.status}")
            _terminal_sms_debug(f"provider_status={provider_status}")
            _terminal_sms_debug(f"provider_message={provider_message}")
            _terminal_sms_debug(f"raw_response={raw}")
            _terminal_sms_debug(
                f"payload={json.dumps(payload, ensure_ascii=False)}"
            )
            _terminal_sms_debug("=====================================")

            if not (200 <= response.status < 300):
                details["reason"] = "non_2xx_response"

                logger.warning(
                    "SMS.ir HTTP non-2xx response phone=%s status=%s body=%s",
                    normalized_phone,
                    response.status,
                    raw,
                )

                return False, details

            if _is_provider_success(provider_status, parsed_response):
                logger.info(
                    "SMS.ir accepted phone=%s http_status=%s provider_status=%s message=%s",
                    normalized_phone,
                    response.status,
                    provider_status,
                    provider_message,
                )

                _terminal_sms_debug(
                    f"accepted phone={normalized_phone} "
                    f"http_status={response.status} "
                    f"provider_status={provider_status} "
                    f"message={provider_message}"
                )

                return True, details

            # اگر پاسخ JSON نبود، HTTP موفق بوده ولی نمی‌توانیم وضعیت داخلی را بفهمیم.
            # برای دیباگ، True برمی‌گردانیم اما raw_response را در details داریم.
            if parsed_response is None:
                details["reason"] = "http_success_non_json_response"

                logger.info(
                    "SMS.ir HTTP success with non-json response phone=%s status=%s body=%s",
                    normalized_phone,
                    response.status,
                    raw,
                )

                _terminal_sms_debug(
                    f"http_success_non_json phone={normalized_phone} "
                    f"status={response.status}"
                )

                return True, details

            details["reason"] = "provider_rejected"

            logger.warning(
                "SMS.ir provider rejected phone=%s http_status=%s provider_status=%s message=%s body=%s",
                normalized_phone,
                response.status,
                provider_status,
                provider_message,
                raw,
            )

            _terminal_sms_debug(
                f"provider_failed phone={normalized_phone} "
                f"http_status={response.status} "
                f"provider_status={provider_status} "
                f"message={provider_message}"
            )

            return False, details

    except error.HTTPError as exc:
        details_body = exc.read().decode("utf-8", errors="replace")
        parsed_response = _parse_smsir_response(details_body)

        logger.warning(
            "SMS.ir HTTPError phone=%s status=%s body=%s",
            normalized_phone,
            exc.code,
            details_body,
        )

        _terminal_sms_debug("========== SMS.IR HTTP ERROR ==========")
        _terminal_sms_debug(f"phone={normalized_phone}")
        _terminal_sms_debug(f"status={exc.code}")
        _terminal_sms_debug(f"body={details_body}")
        _terminal_sms_debug("=======================================")

        return False, {
            "provider": provider,
            "mode": "live",
            "reason": "http_error",
            "phone": normalized_phone,
            "status_code": exc.code,
            "response": details_body,
            "parsed_response": parsed_response,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "SMS.ir unexpected error phone=%s",
            normalized_phone,
        )

        _terminal_sms_debug("========== SMS.IR UNEXPECTED ERROR ==========")
        _terminal_sms_debug(f"phone={normalized_phone}")
        _terminal_sms_debug(f"error={exc}")
        _terminal_sms_debug("=============================================")

        return False, {
            "provider": provider,
            "mode": "live",
            "reason": "unexpected_error",
            "phone": normalized_phone,
            "error": str(exc),
        }
