import os
from datetime import timedelta


class Config:
    """Konfigurasi utama aplikasi Flask PINS.
    Semua nilai sensitif WAJIB diisi lewat environment variable (.env),
    jangan hardcode di kode saat deploy ke hosting produksi.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "ganti-di-env-production")

    # Contoh URI untuk MariaDB di shared hosting (Dewaweb/cPanel):
    # mysql+pymysql://namauser_db:password@localhost/namauser_pins_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://pins_user:password@localhost/pins_db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # penting di shared hosting: koneksi idle sering diputus server
        "pool_recycle": 280,
    }

    JWT_EXPIRES = timedelta(hours=12)

    # Kredensial integrasi dua arah dengan PIJAR (lihat kontrak_api_pijar_pins.md)
    PIJAR_API_KEY = os.environ.get("PIJAR_API_KEY")  # key yang PIJAR kirim ke PINS (validasi masuk)
    PIJAR_API_URL = os.environ.get(
        "PIJAR_API_URL", "https://api.pjujogja.id/api/v1/eksternal"
    )
    PINS_TO_PIJAR_KEY = os.environ.get("PINS_TO_PIJAR_KEY")  # key yang PINS kirim ke PIJAR (request keluar)
