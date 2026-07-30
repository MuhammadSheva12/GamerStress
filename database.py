import os
import json
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
            probabilitas TEXT NOT NULL
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def save_prediction(form, hasil, probabilitas):
    """Simpan satu baris hasil prediksi. Dipanggil setiap kali /predict sukses."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO predictions (
            created_at, usia, jenis_kelamin, status, durasi, sesi_per_hari,
            waktu_mulai, win_rate, kekalahan_beruntun, orientasi, mode_game,
            cara_bermain, rank, hasil, probabilitas
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


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
