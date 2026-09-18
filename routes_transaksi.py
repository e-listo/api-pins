from flask import Blueprint, request, jsonify, g

from models import Transaksi
from auth import login_required, require_role
from services import (
    catat_transaksi,
    edit_transaksi_dasar,
    hapus_transaksi_permanen,
    StokTidakCukupError,
)

bp = Blueprint("transaksi", __name__, url_prefix="/api/v1/transaksi")

# Role asli: 'superadmin', 'Admin Gudang', 'Pengurus Barang Pembantu',
# 'Verifikator', 'Verifikator Utama' (dua role terakhir HANYA baca +
# otorisasi laporan resmi, lihat routes_reports.py -- tidak input transaksi)


def _serialize(t: Transaksi):
    return {
        "id": t.id,
        "nomor_transaksi": t.nomor_transaksi,
        "tipe": t.tipe,
        "barang_id": t.barang_id,
        "jumlah": t.jumlah,
        "gudang_asal_id": t.gudang_asal_id,
        "gudang_tujuan_id": t.gudang_tujuan_id,
        "no_spk": t.no_spk,
        "keterangan": t.keterangan,
        "tanggal": str(t.tanggal),
        "harga_satuan": float(t.harga_satuan or 0),
        "total_nilai": float(t.total_nilai or 0),
        "sisa_stok": t.sisa_stok,
    }


@bp.route("", methods=["GET"])
@login_required
def list_transaksi():
    q = Transaksi.query
    tipe = request.args.get("tipe")
    barang_id = request.args.get("barang_id")
    tanggal_dari = request.args.get("tanggal_dari")
    tanggal_sampai = request.args.get("tanggal_sampai")

    if tipe:
        q = q.filter(Transaksi.tipe == tipe)
    if barang_id:
        q = q.filter(Transaksi.barang_id == barang_id)
    if tanggal_dari:
        q = q.filter(Transaksi.tanggal >= tanggal_dari)
    if tanggal_sampai:
        q = q.filter(Transaksi.tanggal <= tanggal_sampai)

    items = q.order_by(Transaksi.created_at.desc()).limit(200).all()
    return jsonify([_serialize(t) for t in items])


@bp.route("/<transaksi_id>", methods=["GET"])
@login_required
def get_transaksi(transaksi_id):
    t = Transaksi.query.get(transaksi_id)
    if not t:
        return jsonify({"error": "Transaksi tidak ditemukan"}), 404
    return jsonify(_serialize(t))


@bp.route("", methods=["POST"])
@require_role("superadmin", "Admin Gudang", "Pengurus Barang Pembantu")
def create_transaksi():
    data = request.get_json() or {}
    for field in ["tipe", "barang_id", "jumlah"]:
        if not data.get(field):
            return jsonify({"error": f"Field '{field}' wajib diisi"}), 422

    try:
        trx, _ = catat_transaksi(
            tipe=data["tipe"],
            barang_id=data["barang_id"],
            jumlah=int(data["jumlah"]),
            gudang_asal_id=data.get("gudang_asal_id"),
            gudang_tujuan_id=data.get("gudang_tujuan_id"),
            harga_satuan=data.get("harga_satuan", 0),
            no_spk=data.get("no_spk"),
            keterangan=data.get("keterangan"),
            user_id=g.current_user["sub"],
            bidang_upt=data.get("bidang_upt"),
        )
    except StokTidakCukupError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    return jsonify(_serialize(trx)), 201


@bp.route("/<transaksi_id>", methods=["PATCH"])
@require_role("superadmin")
def edit_transaksi(transaksi_id):
    data = request.get_json() or {}
    if "jumlah" not in data:
        return jsonify({"error": "Field 'jumlah' wajib diisi"}), 422
    try:
        trx = edit_transaksi_dasar(
            transaksi_id,
            jumlah_baru=int(data["jumlah"]),
            harga_baru=data.get("harga_satuan"),
            keterangan_baru=data.get("keterangan"),
        )
    except StokTidakCukupError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify(_serialize(trx))


@bp.route("/<transaksi_id>", methods=["DELETE"])
@require_role("superadmin")
def delete_transaksi(transaksi_id):
    try:
        hapus_transaksi_permanen(transaksi_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"status": "terhapus_dan_stok_dikembalikan"})
