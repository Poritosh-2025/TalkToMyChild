from django.db import transaction
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.signing import TimestampSigner, BadSignature
from datetime import timedelta
import random
from .models import OTP, RefreshTokenBlacklist
from .utils import generate_access_token, generate_refresh_token, decode_token
from .selectors import get_user_by_email, get_valid_otp, is_refresh_token_blacklisted
from .tasks import send_otp_email
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_by_id(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


class AuthService:
    @staticmethod
    @transaction.atomic
    def register_user(full_name, email, password, referral_code=None):
        existing = get_user_by_email(email)
        if existing and existing.is_email_verified:
            raise ValueError("Email already registered")
        if existing and not existing.is_email_verified:
            existing.delete()

        user = User.objects.create_user(
            full_name=full_name,
            email=email,
            password=password,
            is_email_verified=False,
            credit_balance=2,
        )
        user.referral_code = f"{user.full_name[:3].upper()}{user.id.hex[:4]}"
        user.save()

        # TODO: handle referral awarding after first call (not in auth module)
        if referral_code:
            # Store referral association for later processing
            pass

        otp_code = f"{random.randint(100000, 999999)}"
        OTP.objects.create(
            user=user,
            code=otp_code,
            otp_type="REGISTER_VERIFY",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_otp_email.delay(email, otp_code, "REGISTER_VERIFY")
        return user

    @staticmethod
    @transaction.atomic
    def verify_otp(email, otp_code, otp_type):

        user = get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        otp = get_valid_otp(user, otp_code, otp_type)
        if not otp:
            raise ValueError("Invalid or expired OTP")

        if otp.failed_attempts >= 5:
            otp.delete()
            raise ValueError("Too many failed attempts. Request a new OTP.")

        if otp.code != otp_code:
            otp.failed_attempts += 1
            otp.save()
            raise ValueError(f"Incorrect OTP. {5 - otp.failed_attempts} attempts left.")

        otp.is_used = True
        otp.save()

        if otp_type == "REGISTER_VERIFY":
            user.is_email_verified = True
            user.save()
            access = generate_access_token(user)
            refresh = generate_refresh_token(user)
            return {"access_token": access, "refresh_token": refresh}
        else:  # PASSWORD_RESET
            signer = TimestampSigner()
            reset_token = signer.sign(str(user.id))
            return {"reset_token": reset_token}

    @staticmethod
    @transaction.atomic
    def resend_otp(email, otp_type):
        user = get_user_by_email(email)
        if not user:
            raise ValueError("User not found")
        if otp_type == "REGISTER_VERIFY" and user.is_email_verified:
            raise ValueError("Email already verified")

        # Invalidate existing OTPs
        OTP.objects.filter(user=user, otp_type=otp_type, is_used=False).delete()

        otp_code = f"{random.randint(100000, 999999)}"
        OTP.objects.create(
            user=user,
            code=otp_code,
            otp_type=otp_type,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_otp_email.delay(email, otp_code, otp_type)
        return user

    @staticmethod
    def authenticate_with_email_password(email, password):
        user = authenticate(username=email, password=password)
        if user and user.is_email_verified:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            access = generate_access_token(user)
            refresh = generate_refresh_token(user)
            return {"access_token": access, "refresh_token": refresh, "user": user}
        raise ValueError("Invalid credentials or unverified email")

    @staticmethod
    @transaction.atomic
    def authenticate_with_google(id_token):
        from .utils import verify_google_id_token

        user_info = verify_google_id_token(id_token)
        if not user_info:
            raise ValueError("Invalid Google token")
        email = user_info["email"]
        user = get_user_by_email(email)
        if not user:
            # Auto-create account
            user = User.objects.create_user(
                email=email,
                full_name=user_info["full_name"] or email.split("@")[0],
                password=None,
                is_email_verified=user_info["is_verified"],
                auth_provider="google",
            )
            user.referral_code = f"{user.full_name[:3].upper()}{user.id.hex[:4]}"
            user.save()
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        access = generate_access_token(user)
        refresh = generate_refresh_token(user)
        return {"access_token": access, "refresh_token": refresh, "user": user}

    @staticmethod
    @transaction.atomic
    def authenticate_with_apple(identity_token, full_name=None):
        from .utils import verify_apple_identity_token

        user_info = verify_apple_identity_token(identity_token)
        if not user_info:
            raise ValueError("Invalid Apple token")
        email = user_info["email"]
        user = get_user_by_email(email)
        if not user:
            user = User.objects.create_user(
                email=email,
                full_name=full_name or email.split("@")[0],
                password=None,
                is_email_verified=True,
                auth_provider="apple",
            )
            user.referral_code = f"{user.full_name[:3].upper()}{user.id.hex[:4]}"
            user.save()
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        access = generate_access_token(user)
        refresh = generate_refresh_token(user)
        return {"access_token": access, "refresh_token": refresh, "user": user}

    @staticmethod
    def refresh_access_token(refresh_token):
        if is_refresh_token_blacklisted(refresh_token):
            raise ValueError("Refresh token has been revoked")
        payload = decode_token(refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token")
        user = get_user_by_id(payload["user_id"])
        if not user:
            raise ValueError("User not found")
        # Rotate: blacklist old, generate new pair
        RefreshTokenBlacklist.objects.create(
            token=refresh_token,
            user=user,
            expires_at=timezone.now() + settings.REFRESH_TOKEN_LIFETIME,
        )
        new_access = generate_access_token(user)
        new_refresh = generate_refresh_token(user)
        return {"access_token": new_access, "refresh_token": new_refresh}

    @staticmethod
    def logout(refresh_token):
        if refresh_token:
            payload = decode_token(refresh_token)
            if payload:
                try:
                    user = User.objects.get(id=payload["user_id"])
                    RefreshTokenBlacklist.objects.create(
                        token=refresh_token,
                        user=user,
                        expires_at=timezone.now() + settings.REFRESH_TOKEN_LIFETIME,
                    )
                except User.DoesNotExist:
                    pass
        return True

    @staticmethod
    @transaction.atomic
    def reset_password_request(email):
        user = get_user_by_email(email)
        if not user or not user.is_email_verified:
            # Do not reveal existence
            return
        # Invalidate existing PASSWORD_RESET OTPs
        OTP.objects.filter(user=user, otp_type="PASSWORD_RESET", is_used=False).delete()
        otp_code = f"{random.randint(100000, 999999)}"
        OTP.objects.create(
            user=user,
            code=otp_code,
            otp_type="PASSWORD_RESET",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        send_otp_email.delay(email, otp_code, "PASSWORD_RESET")

    @staticmethod
    @transaction.atomic
    def reset_password(reset_token, new_password, confirm_password):
        if new_password != confirm_password:
            raise ValueError("Passwords do not match")
        signer = TimestampSigner()
        try:
            user_id = signer.unsign(reset_token, max_age=900)  # 15 minutes
        except BadSignature:
            raise ValueError("Invalid or expired reset token")
        user = get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        user.set_password(new_password)
        user.save()
        # Invalidate all refresh tokens for this user (optional)
        RefreshTokenBlacklist.objects.filter(user=user).delete()
        return True

    @staticmethod
    @transaction.atomic
    def change_password(user, current_password, new_password, confirm_password):
        if new_password != confirm_password:
            raise ValueError("New passwords do not match")
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect")
        user.set_password(new_password)
        user.save()
        # Invalidate all refresh tokens
        RefreshTokenBlacklist.objects.filter(user=user).delete()
        return True
