import jwt
from jwt import PyJWKClient

import config
from utils.response import error

# Cache the JWKS client across warm Lambda invocations
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{config.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        )
    return _jwks_client


def authenticate(event):
    """Verify the Supabase JWT from the Authorization header.

    Supports both HS256 (legacy) and ES256 (current) Supabase tokens.
    Returns (user_id: str, None) on success or (None, error_response) on failure.
    """
    headers = event.get("headers") or {}
    auth_header = headers.get("authorization") or headers.get("Authorization") or ""

    if not auth_header.startswith("Bearer "):
        return None, error("Missing or invalid authorization header", 401)

    token = auth_header.split(" ", 1)[1]
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "HS256":
            payload = jwt.decode(
                token,
                config.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )

        return payload["sub"], None
    except jwt.ExpiredSignatureError:
        return None, error("Token has expired", 401)
    except (jwt.InvalidTokenError, KeyError, ValueError) as e:
        return None, error("Invalid token", 401)
