import jwt
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension
import uuid
from .models import User


# ---------- JWT ----------
def generate_access_token(user):
    lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": timezone.now() + lifetime,
        "iat": timezone.now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user):
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    payload = {
        "user_id": str(user.id),
        "exp": timezone.now() + lifetime,
        "iat": timezone.now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        if not payload:
            raise AuthenticationFailed("Invalid or expired token")
        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")
        return (user, token)


# ---------- OAuth Helpers ----------
def verify_google_id_token(id_token):
    """Verify Google id_token and return user info dict or None."""
    url = "https://oauth2.googleapis.com/tokeninfo"
    resp = requests.get(url, params={"id_token": id_token})
    if resp.status_code != 200:
        return None
    data = resp.json()
    # Verify audience matches your client ID
    if data.get("aud") != settings.GOOGLE_CLIENT_ID:
        return None
    return {
        "email": data["email"],
        "full_name": data.get("name", ""),
        "is_verified": data.get("email_verified", False),
    }


def verify_apple_identity_token(identity_token):
    """Verify Apple identity token using Apple's public keys."""
    # Apple's public keys endpoint
    url = "https://appleid.apple.com/auth/keys"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    keys = resp.json().get("keys", [])
    try:
        # Decode without verification first to get kid and alg
        unverified = jwt.get_unverified_header(identity_token)
        kid = unverified["kid"]
        alg = unverified["alg"]
        # Find matching key
        key_data = None
        for key in keys:
            if key["kid"] == kid:
                key_data = key
                break
        if not key_data:
            return None
        # Construct public key
        from jwt.algorithms import RSAAlgorithm

        public_key = RSAAlgorithm.from_jwk(key_data)
        payload = jwt.decode(
            identity_token,
            public_key,
            algorithms=[alg],
            audience=settings.APPLE_CLIENT_ID,
            options={"verify_exp": True},
        )
        return {
            "email": payload.get("email"),
            "full_name": "",  # Apple only gives name on first sign-in, must be sent from client
            "is_verified": True,
        }
    except Exception:
        return None


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authentication.utils.JWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
