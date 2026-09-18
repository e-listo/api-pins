import datetime
from sqlalchemy import func

from models import db, Barang, Transaksi, TransaksiFifoDetail, Notifikasi


class StokTidakCukupError(Exception):
    """Dipakai saat transaksi keluar/mutasi melebihi stok yang tersedia."""


def generate_nomor_transaksi(tipe: str) -> str:
    prefix = {"masuk": "TRM", "keluar": "TRK", "mutasi": "TRP"}.get(tipe, "TRX")
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}"


def catat_transaksi(
    tipe,
    barang_id,
    jumlah,
    gudang_asal_id=None,
    gudang_tujuan_id=None,
    harga_satuan=0,
    no_spk=None,
    keterangan=None,
    user_id=None,
    bidang_upt=None,
    idempotency_key=None,
    tanggal=None,
):
    """Pengganti Postgres function + trigger untuk mencatat transaksi & update stok.
    Dibungkus row-lock (with_for_update) supaya atomik, setara FOR UPDATE di Postgres.

    Return (transaksi, sudah_ada_sebelumnya: bool)
    """
    if idempotency_key:
        existing = Transaksi.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return existing, True

    barang = Barang.query.with_for_update().get(barang_id)
    if not barang:
        raise ValueError("Barang tidak ditemukan")

    if tipe == "masuk":
        barang.stok += jumlah
    elif tipe == "keluar":
        if barang.stok < jumlah:
            raise StokTidakCukupError(
                f"Stok tersisa {barang.stok}, tidak cukup untuk {jumlah}"
            )
        barang.stok -= jumlah
        _alokasi_fifo(barang_id, jumlah)
    elif tipe == "mutasi":
        if barang.stok < jumlah:
            raise StokTidakCukupError(
                f"Stok tersisa {barang.stok}, tidak cukup untuk mutasi {jumlah}"
            )
        barang.stok -= jumlah
    else:
        raise ValueError("Tipe transaksi tidak dikenal (harus masuk/keluar/mutasi)")

    trx = Transaksi(
        nomor_transaksi=generate_nomor_transaksi(tipe),
        tipe=tipe,
        barang_id=barang_id,
        jumlah=jumlah,
        gudang_asal_id=gudang_asal_id,
        gudang_tujuan_id=gudang_tujuan_id,
        no_spk=no_spk,
        keterangan=keterangan,
        user_id=user_id,
        harga_satuan=harga_satuan,
        total_nilai=(harga_satuan or 0) * jumlah,
        bidang_upt=bidang_upt,
        sisa_stok=barang.stok,
        idempotency_key=idempotency_key,
        tanggal=tanggal or datetime.date.today(),
    )
    db.session.add(trx)

    if barang.stok < barang.stok_minimum:
        db.session.add(
            Notifikasi(
                judul=f"Stok rendah: {barang.nama}",
                pesan=f"Stok {barang.nama} tersisa {barang.stok} (minimum {barang.stok_minimum})",
                tipe="alert_stok",
                target_role="all",
                meta={"barang_id": barang.id, "stok": barang.stok},
            )
        )

    db.session.commit()
    return trx, False


def _alokasi_fifo(barang_id, jumlah_keluar):
    """Alokasikan pengurangan stok ke batch 'masuk' terlama dulu (First In First Out),
    supaya perhitungan harga rata-rata/nilai persediaan tetap akurat.
    """
    batch_masuk = (
        Transaksi.query.filter_by(barang_id=barang_id, tipe="masuk")
        .order_by(Transaksi.created_at.asc())
        .all()
    )
    sisa = jumlah_keluar
    for batch in batch_masuk:
        if sisa <= 0:
            break
        sudah_dipakai = (
            db.session.query(func.coalesce(func.sum(TransaksiFifoDetail.jumlah_diambil), 0))
            .filter(TransaksiFifoDetail.batch_masuk_id == batch.id)
            .scalar()
        )
        tersisa_di_batch = batch.jumlah - sudah_dipakai
        if tersisa_di_batch <= 0:
            continue
        ambil = min(tersisa_di_batch, sisa)
        db.session.add(
            TransaksiFifoDetail(
                batch_masuk_id=batch.id,
                jumlah_diambil=ambil,
                harga_satuan_saat_itu=batch.harga_satuan,
            )
        )
        sisa -= ambil


def edit_transaksi_dasar(transaksi_id, jumlah_baru, harga_baru=None, keterangan_baru=None):
    """Pengganti fungsi edit_transaksi_dasar() Postgres.
    HARUS dipanggil hanya lewat endpoint yang dibatasi role=superadmin.
    """
    trx = Transaksi.query.with_for_update().get(transaksi_id)
    if not trx:
        raise ValueError("Transaksi tidak ditemukan")
    barang = Barang.query.with_for_update().get(trx.barang_id)

    selisih = jumlah_baru - trx.jumlah
    if selisih != 0:
        if trx.tipe == "masuk":
            barang.stok += selisih
        elif trx.tipe in ("keluar", "mutasi"):
            if barang.stok - selisih < 0:
                raise StokTidakCukupError("Revisi ini akan membuat stok menjadi negatif")
            barang.stok -= selisih

    trx.jumlah = jumlah_baru
    if harga_baru is not None:
        trx.harga_satuan = harga_baru
        trx.total_nilai = harga_baru * jumlah_baru
    if keterangan_baru is not None:
        trx.keterangan = keterangan_baru
    trx.sisa_stok = barang.stok

    db.session.commit()
    return trx


def hapus_transaksi_permanen(transaksi_id):
    """Pengganti fungsi hapus_transaksi_permanen() Postgres: rollback stok lalu hapus baris.
    HARUS dipanggil hanya lewat endpoint yang dibatasi role=superadmin.
    """
    trx = Transaksi.query.with_for_update().get(transaksi_id)
    if not trx:
        raise ValueError("Transaksi tidak ditemukan")
    barang = Barang.query.with_for_update().get(trx.barang_id)

    if trx.tipe == "masuk":
        barang.stok -= trx.jumlah
    elif trx.tipe in ("keluar", "mutasi"):
        barang.stok += trx.jumlah

    db.session.delete(trx)
    db.session.commit()
    return True
