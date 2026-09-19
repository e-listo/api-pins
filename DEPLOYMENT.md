# Deployment API PINS

Backend API PINS berjalan sebagai aplikasi Flask melalui Passenger/cPanel dan menggunakan MariaDB.

## Environment wajib

Salin nama variabel dari `.env.example` ke menu Environment Variables pada Python App. Jangan menyalin nilai rahasia ke repository.

- `DATABASE_URL`
- `SECRET_KEY`
- `PIJAR_API_KEY`
- `PIJAR_API_URL`
- `PINS_TO_PIJAR_KEY`

`SECRET_KEY` juga dipakai untuk menandatangani JWT. Aplikasi tidak memakai variabel terpisah bernama `JWT_SECRET_KEY`.

## Deployment manual aman

Jalankan dari application root setelah perubahan di `main` telah ditinjau:

```bash
source /home/USER/virtualenv/api-pins.dpupkp.my.id/3.11/bin/activate
cd /home/USER/api-pins.dpupkp.my.id

git fetch origin
git status -sb
git merge --ff-only origin/main
pip install -r requirements.txt
```

Restart aplikasi melalui cPanel **Setup Python App**, lalu verifikasi:

```bash
curl -fsS https://api-pins.dpupkp.my.id/api/v1/health
```

Respons yang diharapkan:

```json
{"service":"PINS API","status":"ok"}
```

## File khusus hosting

Berkas berikut dibuat atau dikelola pada server dan tidak disimpan di GitHub:

- `.htaccess`
- `.user.ini`
- `php.ini`
- `passenger_wsgi.py`
- `stderr.log`
- `tmp/`
- dump SQL, file password sementara, dan backup

Simpan file sensitif di luar application root dengan permission terbatas, misalnya `chmod 600` untuk file dan `chmod 700` untuk direktori.

## Checklist pascadeploy

- Health check mengembalikan HTTP 200.
- Login dan refresh token berfungsi.
- Endpoint berproteksi menolak request tanpa Bearer token.
- CORS hanya menerima origin frontend yang diizinkan.
- Koneksi MariaDB berhasil dan tidak memakai fallback development.
- Endpoint integrasi menolak API key salah.
- Tidak ada secret, dump SQL, password sementara, atau log produksi yang terlacak Git.

## Rollback

Catat hash sebelum deployment:

```bash
git rev-parse --short HEAD
```

Jika deployment bermasalah, checkout commit stabil sebelumnya atau gunakan branch rollback yang telah disiapkan, lalu restart Python App. Jangan memakai `git reset --hard` sebelum file runtime dan data penting diamankan.
