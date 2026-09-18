"""Endpoint integrasi dua arah PINS <-> PIJAR.
Lihat dokumen kontrak_api_pijar_pins.md untuk kontrak lengkapnya.
Endpoint ini TIDAK memakai JWT user, melainkan API key statis (X-API-KEY),
karena yang memanggil adalah sistem PIJAR, bukan user langsung.
"""

from flask import Blueprint, request, jsonify

from models import Barang
from auth import require_api_key
from services import catat_transaksi, StokTidakCukupError

bp = Blueprint("eksternal", __name__, url_prefix="/api/v1/eksternal")


@bp.route("/stok/<kode_aset>", methods=["GET"])
@require_api_key
def cek_stok(kode_aset):
    """Dipanggil PIJAR sebelum regu berangkat, untuk cek ketersediaan material."""
    b = Barang.query.filter_by(kode_aset=kode_aset).first()
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404
    return jsonify(
        {
            "kode_aset": b.kode_aset,
            "nama": b.nama,
            "stok": b.stok,
            "stok_minimum": b.stok_minimum,
            "satuan": b.satuan,
            "gudang_id": b.gudang_id,
        }
    )


@bp.route("/potong-stok", methods=["POST"])
@require_api_key
def potong_stok():
    """Dipanggil PIJAR setelah regu menyelesaikan pekerjaan pemeliharaan dan
    mencatat material yang terpakai. Wajib idempotency_key untuk mencegah
    stok terpotong dua kali akibat retry jaringan.
    """
    data = request.get_json() or {}

    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        return jsonify({"error": "idempotency_key wajib diisi"}), 422

    kode_aset = data.get("kode_aset")
    jumlah = data.get("jumlah")
    if not kode_aset or not jumlah:
        return jsonify({"error": "kode_aset dan jumlah wajib diisi"}), 422

    b = Barang.query.filter_by(kode_aset=kode_aset).first()
    if not b:
        return jsonify({"error": "Barang tidak ditemukan"}), 404

    try:
        trx, sudah_ada = catat_transaksi(
            tipe="keluar",
            barang_id=b.id,
            jumlah=int(jumlah),
            gudang_asal_id=b.gudang_id,
            no_spk=data.get("referensi"),
            keterangan=data.get("keterangan", "Dipakai untuk pemeliharaan PJU (via PIJAR)"),
            idempotency_key=idempotency_key,
        )
    except StokTidakCukupError as e:
        return jsonify({"status": "gagal", "alasan": str(e)}), 409

    status = "sudah_diproses" if sudah_ada else "sukses"
    http_code = 200 if sudah_ada else 201
    return (
        jsonify(
            {
                "transaksi_id": trx.id,
                "kode_aset": b.kode_aset,
                "jumlah_dipotong": trx.jumlah,
                "sisa_stok": trx.sisa_stok,
                "status": status,
            }
        ),
        http_code,
    )
