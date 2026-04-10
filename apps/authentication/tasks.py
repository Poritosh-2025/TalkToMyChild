from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import OTP


@shared_task
def send_otp_email(email, otp_code, otp_type="REGISTER_VERIFY"):
    subject = f"Your TalkToMyChild {otp_type.replace('_', ' ').title()} OTP"
    message = f"Your OTP code is: {otp_code}\nIt expires in 10 minutes."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])


@shared_task
def delete_expired_otps():
    OTP.objects.filter(expires_at__lt=timezone.now()).delete()
