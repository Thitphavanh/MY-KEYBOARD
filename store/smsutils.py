import re

from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


def normalize_lao_phone(raw_phone):
    """Convert a locally-typed Lao phone number (e.g. "020 5555 5555") to E.164 (+856...)."""
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("856"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]
    return f"+856{digits}"


def _verify_service():
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)


def send_otp(phone_e164):
    """Trigger an SMS OTP to the given E.164 phone number. Raises TwilioRestException on failure."""
    _verify_service().verifications.create(to=phone_e164, channel="sms")


def check_otp(phone_e164, code):
    """Return True if the given OTP code is valid for the phone number."""
    try:
        result = _verify_service().verification_checks.create(to=phone_e164, code=code)
    except TwilioRestException:
        return False
    return result.status == "approved"
