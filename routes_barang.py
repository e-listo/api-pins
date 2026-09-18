from flask import Blueprint, request, jsonify

from models import db, Barang
from auth import login_required, require_role

bp = Blueprint("barang", __name__, url_prefix="/api/v1/barang")

# Role asli dari data produksi (BUKAN role generik yang dipakai sebelumnya):
# 'superadmin', 'Admin Gudang', 'Pengurus Barang Pembantu',
# 'Verifikator', 'Verifikator Utama'


@bp.route("", methods=["GET"])
@login_required
def list_barang():
    q = Barang.query
    kategori = request.args.get("kategori")
    gudang_id = request.args.get("gudang_id")
    stok_rendah = request.args.get("stok_rendah")

    if kategori:
        q = q.filter(Barang.kategori == kategori)
    if gudang_id:
        q = q.filter(Barang.gudang_id == gudang_id)
    if stok_rendah == "true":
        q = q.filter(Barang.stok < Barang.stok_minimum)

    items = q.order_by(Barang.nama.asc()).all()
    return jsonify([b.to_dict() for b in items])


@bp.route("/stok-rendah", methods=["GET"])
@login_required
def stok_rendah():
    items = Barang.query.filter(Barang.stok < Barang.stok_minimum).all()
    return jsonify([b.to_dict() for b in items])


@bp.route("/<barang_id>", methods=["GET"])
@login_required
def get_barang(barang_id):
    b = Barang.query.get(barang_id)
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404
    return jsonify(b.to_dict())


@bp.route("/scan/<kode_aset>", methods=["GET"])
@login_required
def scan_barang(kode_aset):
    """Dipanggil setelah regu lapangan scan QR code aset lewat html5-qrcode."""
    b = Barang.query.filter_by(kode_aset=kode_aset).first()
    if not b:
        return jsonify({"error": "Barang dengan kode tersebut tidak ditemukan"}), 404
    return jsonify(b.to_dict())


@bp.route("/<barang_id>/qrcode", methods=["GET"])
@login_required
def qrcode_payload(barang_id):
    """Payload sederhana yang di-encode jadi QR lewat qrcode.react di frontend."""
    b = Barang.query.get(barang_id)
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404
    return jsonify({"kode_aset": b.kode_aset, "nama": b.nama, "id": b.id})


@bp.route("", methods=["POST"])
@require_role("superadmin", "Admin Gudang")
def create_barang():
    data = request.get_json() or {}
    required = ["kode_aset", "nama", "kategori"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Field wajib diisi: {', '.join(missing)}"}), 422

    if Barang.query.filter_by(kode_aset=data["kode_aset"]).first():
        return jsonify({"error": "Kode aset sudah dipakai barang lain"}), 409

    b = Barang(
        kode_aset=data["kode_aset"],
        nama=data["nama"],
        kategori=data["kategori"],
        satuan=data.get("satuan", "Unit"),
        stok_minimum=data.get("stok_minimum", 10),
        gudang_id=data.get("gudang_id"),
        harga_satuan=data.get("harga_satuan", 0),
        foto_url=data.get("foto_url"),
        keterangan=data.get("keterangan"),
        bidang_upt=data.get("bidang_upt"),
    )
    db.session.add(b)
    db.session.commit()
    return jsonify(b.to_dict()), 201


@bp.route("/<barang_id>", methods=["PATCH"])
@require_role("superadmin", "Admin Gudang", "Pengurus Barang Pembantu")
def update_barang(barang_id):
    """Catatan: kolom 'stok' TIDAK bisa diubah lewat endpoint ini.
    Perubahan stok hanya lewat modul transaksi, supaya riwayat FIFO tetap konsisten.
    """
    b = Barang.query.get(barang_id)
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404

    data = request.get_json() or {}
    field_boleh_diubah = [
        "nama", "kategori", "satuan", "stok_minimum",
        "harga_satuan", "foto_url", "keterangan", "gudang_id",
    ]
    for field in field_boleh_diubah:
        if field in data:
            setattr(b, field, data[field])

    db.session.commit()
    return jsonify(b.to_dict())


@bp.route("/<barang_id>", methods=["DELETE"])
@require_role("superadmin")
def delete_barang(barang_id):
    b = Barang.query.get(barang_id)
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404
    db.session.delete(b)
    db.session.commit()
    return jsonify({"status": "terhapus"})
