import requests as http_client

import config
from db import get_cursor
from middleware.auth import authenticate
from utils.response import error, get_body, success


def handle(event, method, path):
    sub = path.replace("/api/auth", "").strip("/")

    if method == "POST" and sub == "signup":
        return signup(event)
    elif method == "POST" and sub == "login":
        return login(event)
    elif method == "POST" and sub == "refresh":
        return refresh(event)
    elif method == "POST" and sub == "logout":
        return logout(event)
    elif method == "GET" and sub == "me":
        return me(event)

    return error("Not found", 404)


def _supabase_headers():
    return {
        "apikey": config.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }


def _ensure_profile(user_data):
    user_id = user_data["id"]
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM profiles WHERE id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO profiles (id, email, display_name) VALUES (%s, %s, %s)",
                (
                    user_id,
                    user_data.get("email", ""),
                    user_data.get("user_metadata", {}).get("display_name"),
                ),
            )


def signup(event):
    body = get_body(event)
    if not body:
        return error("JSON body is required", 400)

    email = body.get("email")
    password = body.get("password")
    display_name = body.get("display_name")

    if not email or not password:
        return error("Email and password are required", 422)

    resp = http_client.post(
        f"{config.SUPABASE_URL}/auth/v1/signup",
        headers=_supabase_headers(),
        json={
            "email": email,
            "password": password,
            "data": {"display_name": display_name} if display_name else {},
        },
    )

    if resp.status_code >= 400:
        sb_error = resp.json()
        msg = sb_error.get("error_description") or sb_error.get("msg") or sb_error.get("error") or "Signup failed"
        return error(msg, resp.status_code)

    result = resp.json()

    if result.get("access_token"):
        _ensure_profile(result["user"])
        return success({
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "expires_in": result.get("expires_in"),
            "user": {"id": result["user"]["id"], "email": result["user"]["email"]},
        }, 201)

    return success({"message": "Check your email to confirm your account"}, 201)


def login(event):
    body = get_body(event)
    if not body:
        return error("JSON body is required", 400)

    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return error("Email and password are required", 422)

    resp = http_client.post(
        f"{config.SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=_supabase_headers(),
        json={"email": email, "password": password},
    )

    if resp.status_code >= 400:
        sb_error = resp.json()
        msg = sb_error.get("error_description") or sb_error.get("msg") or sb_error.get("error") or "Invalid credentials"
        return error(msg, 401)

    result = resp.json()
    _ensure_profile(result["user"])

    return success({
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_in": result.get("expires_in"),
        "user": {"id": result["user"]["id"], "email": result["user"]["email"]},
    })


def refresh(event):
    body = get_body(event)
    if not body or not body.get("refresh_token"):
        return error("refresh_token is required", 400)

    resp = http_client.post(
        f"{config.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
        headers=_supabase_headers(),
        json={"refresh_token": body["refresh_token"]},
    )

    if resp.status_code >= 400:
        msg = resp.json().get("error_description") or "Invalid refresh token"
        return error(msg, 401)

    result = resp.json()
    return success({
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_in": result.get("expires_in"),
    })


def logout(event):
    user_id, err = authenticate(event)
    if err:
        return err
    return success("Logged out")


def me(event):
    user_id, err = authenticate(event)
    if err:
        return err

    with get_cursor() as cur:
        cur.execute("SELECT * FROM profiles WHERE id = %s", (user_id,))
        profile = cur.fetchone()

    if not profile:
        return error("Profile not found", 404)

    return success({
        "id": str(profile["id"]),
        "email": profile["email"],
        "display_name": profile["display_name"],
        "currency": profile["currency"],
        "created_at": profile["created_at"].isoformat() if profile["created_at"] else None,
    })
