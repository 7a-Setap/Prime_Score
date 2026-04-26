"""Profile routes for viewing and updating account details."""

import logging

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db.connection import DBContext

profile_bp = Blueprint("profile", __name__)
logger = logging.getLogger(__name__)


@profile_bp.route("/profile", methods=["GET"])
def get_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        with DBContext(dict_cursor=True) as (_, cursor):
            cursor.execute(
                "SELECT username, email, display_name, bio FROM users WHERE user_id = %s",
                (session["user_id"],),
            )
            row = cursor.fetchone()
    except RuntimeError:
        return jsonify({"error": "Database unavailable"}), 503
    except Exception:
        logger.exception("get_profile error")
        return jsonify({"error": "Could not load profile"}), 500

    if not row:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "username": row["username"],
            "email": row["email"] or "",
            "display_name": row["display_name"] or "",
            "bio": row["bio"] or "",
        }
    ), 200


@profile_bp.route("/profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    bio = (data.get("bio") or "").strip()

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(username) > 50:
        return jsonify({"error": "Username must be 50 characters or fewer"}), 400
    if email and "@" not in email:
        return jsonify({"error": "Please enter a valid email address"}), 400
    if len(display_name) > 100:
        return jsonify({"error": "Display name must be 100 characters or fewer"}), 400
    if len(bio) > 500:
        return jsonify({"error": "Bio must be 500 characters or fewer"}), 400

    try:
        with DBContext(dict_cursor=True) as (_, cursor):
            cursor.execute(
                "SELECT user_id FROM users WHERE username = %s AND user_id <> %s",
                (username, session["user_id"]),
            )
            if cursor.fetchone():
                return jsonify({"error": "Username already taken"}), 409

            if email:
                cursor.execute(
                    "SELECT user_id FROM users WHERE email = %s AND user_id <> %s",
                    (email, session["user_id"]),
                )
                if cursor.fetchone():
                    return jsonify({"error": "Email already registered"}), 409

            cursor.execute(
                """
                UPDATE users
                SET username = %s, email = %s, display_name = %s, bio = %s
                WHERE user_id = %s
                """,
                (username, email or None, display_name or None, bio or None, session["user_id"]),
            )
    except RuntimeError:
        return jsonify({"error": "Database unavailable"}), 503
    except Exception:
        logger.exception("update_profile error")
        return jsonify({"error": "Could not save profile"}), 500

    session["username"] = username
    session["display_name"] = display_name

    return jsonify(
        {
            "message": "Profile updated successfully",
            "username": username,
            "email": email,
            "display_name": display_name,
            "bio": bio,
        }
    ), 200


@profile_bp.route("/change-password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password are required"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    try:
        with DBContext(dict_cursor=True) as (_, cursor):
            cursor.execute(
                "SELECT password_hash FROM users WHERE user_id = %s",
                (session["user_id"],),
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "User not found"}), 404
            if not check_password_hash(row["password_hash"], current_password):
                return jsonify({"error": "Current password is incorrect"}), 401

            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (generate_password_hash(new_password), session["user_id"]),
            )
    except RuntimeError:
        return jsonify({"error": "Database unavailable"}), 503
    except Exception:
        logger.exception("change_password error")
        return jsonify({"error": "Could not change password"}), 500

    return jsonify({"message": "Password changed successfully"}), 200
