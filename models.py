import uuid
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


class BidangUPT(db.Model):
    __tablename__ = "bidang_upt"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(150), nullable=False, unique=True)
    keterangan = db.Column(db.Text)
    tipe = db.Column(db.String(50), default="Bidang")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Bidang(db.Model):
    __tablename__ = "bidang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(150), nullable=False)
    kode = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Gudang(db.Model):
    __tablename__ = "gudang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(150), nullable=False)
    alamat = db.Column(db.Text)
    kode_lokasi = db.Column(db.String(50))
    bidang_id = db.Column(db.String(36), db.ForeignKey("bidang_upt.id", ondelete="SET NULL"))
    keterangan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Kategori(db.Model):
    __tablename__ = "kategori"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(150), nullable=False)
    prefix = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KategoriBarang(db.Model):
    __tablename__ = "kategori_barang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(150), nullable=False, unique=True)
    kode = db.Column(db.String(50), nullable=False, unique=True)
    deskripsi = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SatuanBarang(db.Model):
    __tablename__ = "satuan_barang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nama = db.Column(db.String(100), nullable=False, unique=True)
    singkatan = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Pegawai(db.Model):
    __tablename__ = "pegawai"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nip = db.Column(db.String(30), nullable=False, unique=True)
    nama = db.Column(db.String(150), nullable=False)
    jabatan = db.Column(db.String(150))
    role = db.Column(db.String(30), nullable=False, default="viewer")
    bidang_id = db.Column(db.String(36), db.ForeignKey("bidang_upt.id", ondelete="SET NULL"))
    foto_url = db.Column(db.String(255))
    email = db.Column(db.String(150))
    status = db.Column(db.String(20), default="Aktif")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OperatorGudang(db.Model):
    __tablename__ = "operator_gudang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    pegawai_id = db.Column(db.String(36), db.ForeignKey("pegawai.id", ondelete="CASCADE"))
    gudang_id = db.Column(db.String(36), db.ForeignKey("gudang.id", ondelete="CASCADE"))
    __table_args__ = (db.UniqueConstraint("pegawai_id", "gudang_id"),)


class Barang(db.Model):
    __tablename__ = "barang"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    kode_aset = db.Column(db.String(100), nullable=False)
    nama = db.Column(db.String(200), nullable=False)
    kategori = db.Column(db.String(100), nullable=False)
    satuan = db.Column(db.String(50), nullable=False, default="Unit")
    stok = db.Column(db.Integer, nullable=False, default=0)
    stok_minimum = db.Column(db.Integer, nullable=False, default=10)
    gudang_id = db.Column(db.String(36), db.ForeignKey("gudang.id"))
    harga_satuan = db.Column(db.BigInteger, nullable=False, default=0)
    foto_url = db.Column(db.String(255))
    keterangan = db.Column(db.Text)
    bidang_upt = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "kode_aset": self.kode_aset,
            "nama": self.nama,
            "kategori": self.kategori,
            "satuan": self.satuan,
            "stok": self.stok,
            "stok_minimum": self.stok_minimum,
            "gudang_id": self.gudang_id,
            "harga_satuan": self.harga_satuan,
            "foto_url": self.foto_url,
            "keterangan": self.keterangan,
            "bidang_upt": self.bidang_upt,
        }


class Transaksi(db.Model):
    __tablename__ = "transaksi"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nomor_transaksi = db.Column(db.String(50), nullable=False, unique=True)
    tipe = db.Column(db.Enum("masuk", "keluar", "mutasi", name="tipe_transaksi"), nullable=False)
    barang_id = db.Column(db.String(36), db.ForeignKey("barang.id"))
    jumlah = db.Column(db.Integer, nullable=False)
    gudang_asal_id = db.Column(db.String(36), db.ForeignKey("gudang.id"))
    gudang_tujuan_id = db.Column(db.String(36), db.ForeignKey("gudang.id"))
    no_spk = db.Column(db.String(100))
    keterangan = db.Column(db.Text)
    tanggal = db.Column(db.Date, nullable=False, default=date.today)
    user_id = db.Column(db.String(36))
    harga_satuan = db.Column(db.Numeric(18, 2), default=0)
    total_nilai = db.Column(db.Numeric(18, 2), default=0)
    bidang_upt = db.Column(db.String(150))
    sisa_stok = db.Column(db.Integer, default=0)
    idempotency_key = db.Column(db.String(150), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TransaksiFifoDetail(db.Model):
    __tablename__ = "transaksi_fifo_detail"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    transaksi_keluar_id = db.Column(db.String(36), db.ForeignKey("transaksi.id", ondelete="CASCADE"))
    batch_masuk_id = db.Column(db.String(36), db.ForeignKey("transaksi.id", ondelete="CASCADE"))
    jumlah_diambil = db.Column(db.Integer, nullable=False)
    harga_satuan_saat_itu = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notifikasi(db.Model):
    __tablename__ = "notifikasi"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    judul = db.Column(db.String(200), nullable=False)
    pesan = db.Column(db.Text, nullable=False)
    tipe = db.Column(
        db.Enum("alert_stok", "transaksi", "barang", "failed_login", "info", name="tipe_notif"),
        nullable=False,
        default="info",
    )
    dibaca = db.Column(db.Boolean, default=False)
    target_role = db.Column(db.String(50), default="all")
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_log"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36))
    nip = db.Column(db.String(30))
    nama_user = db.Column(db.String(150))
    aksi = db.Column(db.String(100), nullable=False)
    tabel = db.Column(db.String(100))
    detail = db.Column(db.JSON)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AppSettings(db.Model):
    __tablename__ = "app_settings"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    setting_key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PengaturanSistem(db.Model):
    __tablename__ = "pengaturan_sistem"
    id = db.Column(db.Integer, primary_key=True)
    maintenance_mode = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
