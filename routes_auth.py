from flask import Blueprint, request, jsonify, g

from models import Pegawai
from auth import verify_password, generate_token, login_required, hash_password

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    identifier = data.get("nip") or data.get("email")
    password = data.get("password")
    if not identifier or not password:
        return jsonify({"error": "nip/email dan password wajib diisi"}), 400

    pegawai = Pegawai.query.filter(
        (Pegawai.nip == identifier) | (Pegawai.email == identifier)
    ).first()

    if not pegawai or not verify_password(password, pegawai.password_hash):
        return jsonify({"error": "NIP/email atau password salah"}), 401
    if pegawai.status != "Aktif":
        return jsonify({"error": "Akun tidak aktif, hubungi superadmin"}), 403

    token = generate_token(pegawai)
    return jsonify(
        {
            "token": token,
            "pegawai": {
                "id": pegawai.id,
                "nama": pegawai.nama,
                "role": pegawai.role,
                "nip": pegawai.nip,
            },
        }
    )


@bp.route("/me", methods=["GET"])
@login_required
def me():
    pegawai = Pegawai.query.get(g.current_user["sub"])
    if not pegawai:
        return jsonify({"error": "Pengguna tidak ditemukan"}), 404
    return jsonify(
        {
            "id": pegawai.id,
            "nip": pegawai.nip,
            "nama": pegawai.nama,
            "role": pegawai.role,
            "jabatan": pegawai.jabatan,
            "foto_url": pegawai.foto_url,
        }
    )


@bp.route("/me/password", methods=["PATCH"])
@login_required
def ganti_password():
    from models import db

    data = request.get_json() or {}
    password_baru = data.get("password_baru")
    if not password_baru or len(password_baru) < 8:
        return jsonify({"error": "Password baru minimal 8 karakter"}), 422

    pegawai = Pegawai.query.get(g.current_user["sub"])
    pegawai.password_hash = hash_password(password_baru)
    db.session.commit()
    return jsonify({"status": "password_diperbarui"})
