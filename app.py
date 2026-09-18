from flask import Flask, jsonify

from config import Config
from models import db


def create_app():
    app = Flask(__name__)
    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": ["https://pins.dpupkp.my.id"]}}, supports_credentials=True)

    app.config.from_object(Config)
    db.init_app(app)

    from routes_auth import bp as auth_bp
    from routes_barang import bp as barang_bp
    from routes_transaksi import bp as transaksi_bp
    from routes_eksternal import bp as eksternal_bp
    from routes_reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(barang_bp)
    app.register_blueprint(transaksi_bp)
    app.register_blueprint(eksternal_bp)
    app.register_blueprint(reports_bp)

    # TODO modul berikutnya (pola CRUD sama seperti routes_barang.py):
    # - routes_master.py   -> /api/v1/gudang, /api/v1/kategori-barang, /api/v1/satuan-barang
    # - routes_pegawai.py  -> /api/v1/pegawai, /api/v1/operator-gudang
    # - routes_notifikasi.py -> /api/v1/notifikasi

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "PINS API"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint tidak ditemukan"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Terjadi kesalahan pada server"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
