import os
import json
import secrets
import string
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    """Buat tabel predictions kalau belum ada. Dipanggil sekali saat app start."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,

            usia TEXT,
            jenis_kelamin TEXT,
            status TEXT,
            durasi TEXT,
            sesi_per_hari TEXT,
            waktu_mulai TEXT,
            win_rate TEXT,
            kekalahan_beruntun TEXT,
            orientasi TEXT,
            mode_game TEXT,
            cara_bermain TEXT,
            rank TEXT,

            hasil TEXT NOT NULL,
            probabilitas TEXT NOT NULL,

            kode_akses TEXT UNIQUE
        )
        """
    )
    # Kolom kode_akses ditambahkan belakangan; ALTER ini aman dijalankan
    # berulang kali (kalau kolom sudah ada, IF NOT EXISTS akan skip).
    cur.execute(
        "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS kode_akses TEXT UNIQUE"
    )
    conn.commit()
    cur.close()
    conn.close()


def _generate_kode_akses(cur):
    """Generate kode akses 8 karakter (huruf besar + angka) yang belum
    dipakai baris lain. Dicek unik di DB supaya gak pernah tabrakan."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        kode = "".join(secrets.choice(alphabet) for _ in range(8))
        cur.execute("SELECT 1 FROM predictions WHERE kode_akses = %s", (kode,))
        if cur.fetchone() is None:
            return kode


def save_prediction(form, hasil, probabilitas):
    """Simpan satu baris hasil prediksi. Dipanggil setiap kali /predict sukses.
    Mengembalikan kode_akses yang digenerate, supaya bisa ditampilkan ke user
    dan dipakai lagi nanti untuk membuka hasil ini via /cek-hasil."""
    conn = get_connection()
    cur = conn.cursor()

    kode_akses = _generate_kode_akses(cur)

    cur.execute(
        """
        INSERT INTO predictions (
            created_at, usia, jenis_kelamin, status, durasi, sesi_per_hari,
            waktu_mulai, win_rate, kekalahan_beruntun, orientasi, mode_game,
            cara_bermain, rank, hasil, probabilitas, kode_akses
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            datetime.now(),
            form.get("usia"),
            form.get("jenis_kelamin"),
            form.get("status"),
            form.get("durasi"),
            form.get("sesi_per_hari"),
            form.get("waktu_mulai"),
            form.get("win_rate"),
            form.get("kekalahan_beruntun"),
            form.get("orientasi"),
            form.get("mode_game"),
            form.get("cara_bermain"),
            form.get("rank"),
            hasil,
            json.dumps(probabilitas, ensure_ascii=False),
            kode_akses,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    return kode_akses


def get_prediction_by_kode(kode_akses):
    """Ambil satu hasil prediksi berdasarkan kode akses. Dipakai di /cek-hasil.
    Return None kalau kode gak ditemukan."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM predictions WHERE kode_akses = %s",
        (kode_akses.strip().upper(),),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_all_predictions():
    """Ambil semua riwayat prediksi, terbaru duluan. Dipakai untuk halaman statistik/riwayat."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


def get_prediction_summary():
    """Hitung ringkasan jumlah per kategori hasil (Rendah/Sedang/Tinggi), untuk statistik."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT hasil, COUNT(*) as jumlah FROM predictions GROUP BY hasil")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row["hasil"]: row["jumlah"] for row in rows}
