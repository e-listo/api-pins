import datetime
from functools import wraps

import jwt
from flask import request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_token(pegawai) -> str:
    """Buat JWT berisi identitas & role pegawai.
    Menggantikan Supabase Auth + get_my_role()/get_my_bidang() dari skema lama.
    """
    payload = {
        "sub": pegawai.id,
        "nip": pegawai.nip,
        "nama": pegawai.nama,
        "role": pegawai.role,
        "bidang_id": pegawai.bidang_id,
        "exp": datetime.datetime.utcnow() + current_app.config["JWT_EXPIRES"],
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def login_required(f):
    """Wajib ada Bearer token JWT yang valid. Hasil decode disimpan di g.current_user."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token tidak ditemukan"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token sudah kedaluwarsa, silakan login ulang"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token tidak valid"}), 401
        g.current_user = payload
        return f(*args, **kwargs)

    return wrapper


def require_role(*roles):
    """Dekorator otorisasi berbasis role, pengganti RLS policy Postgres.
    Contoh: @require_role('superadmin', 'Admin Gudang')
    """

    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if g.current_user.get("role") not in roles:
                return jsonify({"error": "Akses ditolak untuk role ini"}), 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


def require_api_key(f):
    """Otorisasi khusus endpoint integrasi sistem-ke-sistem (PIJAR <-> PINS).
    Tidak memakai JWT user, melainkan API key statis di header X-API-KEY.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        expected = current_app.config.get("PIJAR_API_KEY")
        if not expected or key != expected:
            return jsonify({"error": "API key tidak valid"}), 401
        return f(*args, **kwargs)

    return wrapper
