import random
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

OTP_TTL_MINUTES = 10


def generate_otp():
    return f"{random.randint(0, 999999):06d}"


def otp_expiry():
    return timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)


def send_otp_email(email, code):
    send_mail(
        subject="ລະຫັດຢືນຢັນ — NexByte Computer",
        message=(
            f"ລະຫັດຢືນຢັນຂອງທ່ານແມ່ນ: {code}\n\n"
            f"ລະຫັດນີ້ຈະໝົດອາຍຸພາຍໃນ {OTP_TTL_MINUTES} ນາທີ."
        ),
        from_email=None,
        recipient_list=[email],
    )
