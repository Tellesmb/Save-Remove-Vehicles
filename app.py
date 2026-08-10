from datetime import datetime, timedelta, timezone
import os
import secrets

import jwt
from flask import Flask, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

# For this class demonstration only.
# In production, always provide the secret through an environment variable.
JWT_SECRET = os.getenv("JWT_SECRET", "cs361-demo-secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_SECONDS = 3600

# Temporary in-memory storage.
# Restarting the service resets this data.
users = {
    "brian": {
        "email": "brian@example.com",
        "password_hash": generate_password_hash("12345")
    }
}

refresh_tokens = {}

reset_tokens = {
    "abc123-reset-token": {
        "username": "brian",
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
}


def error_response(message, status_code):
    """Return a consistent JSON error response."""
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def find_user(identifier):
    """Find a user by username or email."""
    if not identifier:
        return None, None

    identifier = identifier.lower()

    for username, user in users.items():
        if username.lower() == identifier:
            return username, user

        if user["email"].lower() == identifier:
            return username, user

    return None, None


def create_access_token(username):
    """Create a one-hour JWT access token."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_SECONDS)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def create_refresh_token(username):
    """Create and store a refresh token."""
    token = secrets.token_urlsafe(32)

    refresh_tokens[token] = {
        "username": username,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24)
    }

    return token


def remove_user_refresh_tokens(username):
    """Invalidate every refresh token belonging to a user."""
    tokens_to_remove = []

    for token, token_data in refresh_tokens.items():
        if token_data["username"] == username:
            tokens_to_remove.append(token)

    for token in tokens_to_remove:
        refresh_tokens.pop(token, None)


@app.get("/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Auth microservice is running"
    }), 200


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("A JSON request body is required", 400)

    identifier = data.get("username") or data.get("email")
    password = data.get("password")

    if not identifier or not password:
        return error_response(
            "username or email and password are required",
            400
        )

    username, user = find_user(identifier)

    if user is None or not check_password_hash(
        user["password_hash"],
        password
    ):
        return error_response("Invalid credentials", 401)

    access_token = create_access_token(username)
    refresh_token = create_refresh_token(username)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_SECONDS
    }), 200


@app.post("/auth/refresh")
def refresh():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("A JSON request body is required", 400)

    old_refresh_token = data.get("refresh_token")

    if not old_refresh_token:
        return error_response("refresh_token is required", 400)

    token_data = refresh_tokens.get(old_refresh_token)

    if token_data is None:
        return error_response(
            "Invalid or expired refresh token",
            401
        )

    if token_data["expires_at"] <= datetime.now(timezone.utc):
        refresh_tokens.pop(old_refresh_token, None)

        return error_response(
            "Invalid or expired refresh token",
            401
        )

    username = token_data["username"]

    # Rotate the refresh token.
    refresh_tokens.pop(old_refresh_token, None)

    new_access_token = create_access_token(username)
    new_refresh_token = create_refresh_token(username)

    return jsonify({
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": ACCESS_TOKEN_SECONDS
    }), 200


@app.post("/auth/reset-password")
def reset_password():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("A JSON request body is required", 400)

    reset_token = data.get("reset_token")
    new_password = data.get("new_password")

    if not reset_token or not new_password:
        return error_response(
            "reset_token and new_password are required",
            400
        )

    if len(new_password) < 8:
        return error_response(
            "Password must contain at least 8 characters",
            400
        )

    token_data = reset_tokens.get(reset_token)

    if token_data is None:
        return error_response(
            "Invalid or expired reset token",
            401
        )

    if token_data["expires_at"] <= datetime.now(timezone.utc):
        reset_tokens.pop(reset_token, None)

        return error_response(
            "Invalid or expired reset token",
            401
        )

    username = token_data["username"]

    users[username]["password_hash"] = generate_password_hash(
        new_password
    )

    # Reset tokens are single-use.
    reset_tokens.pop(reset_token, None)

    # Password reset invalidates existing sessions.
    remove_user_refresh_tokens(username)

    return jsonify({
        "status": "success",
        "message": "Password updated successfully."
    }), 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False
    )