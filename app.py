from flask import Flask, render_template, request
import joblib
import pandas as pd
import database

app = Flask(__name__)

# ==========================================================
# LOAD MODEL
# ==========================================================

model = joblib.load("model/random_forest_model.pkl")
label_encoder = joblib.load("model/label_encoder.pkl")

# ==========================================================
# INIT DATABASE
# ==========================================================

database.init_db()

# ==========================================================
# URUTAN FITUR (WAJIB SAMA DENGAN MODEL)
# ==========================================================

FEATURE_ORDER = [
    "Usia_Encode",
    "JenisKelamin_Encode",
    "Status_Encode",
    "Durasi_Encode",
    "Frekuensi_Encode",
    "Waktu_Encode",
    "WinRate_Encode",
    "LoseStreak_Encode",
    "Orientasi_Encode",
    "Mode_Encode",
    "CaraMain_Encode",
    "Rank_Encode",
]

# ==========================================================
# ENCODING
# ==========================================================
# Catatan: "> 28 tahun" dan "Lainnya" ada sebagai opsi di form,
# tapi TIDAK PERNAH muncul di 155 data training (lihat Bab 4).
# Supaya form tetap terbuka untuk publik tanpa model "menebak buta"
# di luar apa yang pernah dipelajari, kedua kategori ini di-fallback
# ke kategori terdekat yang memang ada di data training.

usia_map = {
    "< 17 tahun": 0,
    "17–20 tahun": 1,
    "21–24 tahun": 2,
    "25–28 tahun": 3,
    "> 28 tahun": 3,  # <-- FALLBACK, BUKAN 4
}

jk_map = {
    "Laki-laki": 0,
    "Perempuan": 1,
}

status_map = {
    "Bekerja": 0,
    "Pelajar/Mahasiswa": 1,
    "Pelajar/Mahasiswa sambil bekerja": 2,
    "Lainnya": 0,  # <-- FALLBACK, BUKAN 3
}

durasi_map = {
    "Kurang dari 30 menit": 0,
    "30–60 menit": 1,
    "61–120 menit": 2,
    "121–180 menit": 3,
    "Lebih dari 180 menit": 4,
}

frekuensi_map = {
    "1 sesi": 0,
    "2 sesi": 1,
    "3 sesi": 2,
    "4 sesi": 3,
    "Lebih dari 4 sesi": 4,
}

waktu_map = {
    "Dini hari (00.00–04.59)": 0,
    "Pagi (05.00–10.59)": 1,
    "Siang (11.00–14.59)": 2,
    "Sore (15.00–17.59)": 3,
    "Malam (18.00–23.59)": 4,
}

winrate_map = {
    "Kurang dari 45%": 0,
    "45%–49%": 1,
    "50%–54%": 2,
    "55%–59%": 3,
    "60% atau lebih": 4,
}

losestreak_map = {
    "Tidak pernah kalah beruntun": 0,
    "2 kali": 1,
    "3 kali": 2,
    "4 kali": 3,
    "5 kali atau lebih": 4,
}

orientasi_map = {
    "Kasual": 0,
    "Kompetitif": 1,
}

mode_map = {
    "Brawl": 0,
    "Classic": 1,
    "Mode lainnya": 2,
    "Ranked": 3,
}

caramain_map = {
    "Komunitas": 0,
    "Duo/Trio/Squad": 1,
    "Solo": 2,
}

rank_map = {
    "Warrior": 0,
    "Elite": 1,
    "Master": 2,
    "Grandmaster": 3,
    "Epic": 4,
    "Legend": 5,
    "Mythic": 6,
    "Mythical Honor": 7,
    "Mythical Glory": 8,
    "Mythical Immortal": 9,
}

# ==========================================================
# ENCODE INPUT DARI FORM HTML
# ==========================================================

def encode_input(form):

    encoded = {
        "Usia_Encode": usia_map[form["usia"]],
        "JenisKelamin_Encode": jk_map[form["jenis_kelamin"]],
        "Status_Encode": status_map[form["status"]],
        "Durasi_Encode": durasi_map[form["durasi"]],
        "Frekuensi_Encode": frekuensi_map[form["sesi_per_hari"]],
        "Waktu_Encode": waktu_map[form["waktu_mulai"]],
        "WinRate_Encode": winrate_map[form["win_rate"]],
        "LoseStreak_Encode": losestreak_map[form["kekalahan_beruntun"]],
        "Orientasi_Encode": orientasi_map[form["orientasi"]],
        "Mode_Encode": mode_map[form["mode_game"]],
        "CaraMain_Encode": caramain_map[form["cara_bermain"]],
        "Rank_Encode": rank_map[form["rank"]],
    }

    return pd.DataFrame([encoded])[FEATURE_ORDER]


# ==========================================================
# FAKTOR YANG MEMPENGARUHI
# ==========================================================

def get_faktor(form):

    faktor = []

    if form["sesi_per_hari"] in [
        "3 sesi",
        "4 sesi",
        "Lebih dari 4 sesi"
    ]:
        faktor.append("Frekuensi bermain tinggi")

    if form["durasi"] in [
        "121–180 menit",
        "Lebih dari 180 menit"
    ]:
        faktor.append("Durasi bermain panjang")

    if form["kekalahan_beruntun"] in [
        "4 kali",
        "5 kali atau lebih"
    ]:
        faktor.append("Kekalahan beruntun tinggi")

    if form["orientasi"] == "Kompetitif":
        faktor.append("Orientasi bermain kompetitif")

    if form["rank"] in [
        "Epic",
        "Legend",
        "Mythic",
        "Mythical Honor",
        "Mythical Glory",
        "Mythical Immortal"
    ]:
        faktor.append("Rank tinggi")

    if len(faktor) == 0:
        faktor.append("Pola bermain normal")

    return faktor


# ==========================================================
# AMBIL DATA DATASET (untuk halaman /dataset)
# ==========================================================

def get_sheet_data():

    try:

        df = pd.read_excel("data/Dataset_Kuesioner_Ordinal.xlsx")

        return df

    except Exception as e:

        print("ERROR :", e)

        return None

# ==========================================================
# ROUTES
# ==========================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["GET", "POST"])
def predict():

    if request.method == "POST":

        try:

            X_input = encode_input(request.form)

            pred = model.predict(X_input)[0]

            hasil = label_encoder.inverse_transform([pred])[0]

            probability = model.predict_proba(X_input)[0]

            probabilitas = {
                label_encoder.classes_[i]: round(probability[i] * 100, 2)
                for i in range(len(label_encoder.classes_))
            }

            faktor_list = get_faktor(request.form)

            database.save_prediction(request.form, hasil, probabilitas)

            return render_template(
                "result.html",
                hasil=hasil,
                probabilitas=probabilitas,
                faktor_list=faktor_list
            )

        except KeyError as e:
            return render_template(
                "predict.html",
                error=f"Ada pilihan yang belum lengkap atau tidak valid ({e}). Silakan periksa kembali form Anda."
            )

        except Exception:
            return render_template(
                "predict.html",
                error="Terjadi kendala saat memproses data Anda. Silakan periksa kembali isian form dan coba lagi."
            )

    return render_template("predict.html")


@app.route("/result")
def result():

    return render_template(
        "result.html",
        hasil="-",
        probabilitas={},
        faktor_list=[]
    )


@app.route("/dataset")
def dataset():

    df = get_sheet_data()

    if df is None:
        return render_template(
            "dataset.html",
            total=0,
            badge="Tidak ada data",
            jumlah_provinsi=0,
            rendah_pct=0,
            sedang_pct=0,
            tinggi_pct=0,
            ranked_pct=0,
            classic_pct=0,
            brawl_pct=0,
            lainnya_pct=0,
            wilayah_data=[],
            feature_importance=[]
        )

    total = len(df)

    # =============================
    # NAMA KOLOM
    # =============================

    kolom_provinsi = "  8. Domisili — Provinsi  "
    kolom_mode = "16.  Mode permainan yang paling sering Anda mainkan"
    kolom_stres = "Kategori_Stres"

    # =============================
    # JUMLAH PROVINSI
    # =============================

    jumlah_provinsi = 0
    wilayah_data = []

    if kolom_provinsi in df.columns:

        jumlah_provinsi = df[kolom_provinsi].nunique()

        wilayah = df[kolom_provinsi].value_counts()

        for provinsi, jumlah in wilayah.items():

            wilayah_data.append({
                "nama": provinsi,
                "jumlah": int(jumlah),
                "pct": round(jumlah / total * 100, 1)
            })

    # =============================
    # DISTRIBUSI STRES
    # =============================

    rendah_pct = sedang_pct = tinggi_pct = 0

    if kolom_stres in df.columns:

        rendah = (df[kolom_stres] == "Stres Rendah").sum()
        sedang = (df[kolom_stres] == "Stres Sedang").sum()
        tinggi = (df[kolom_stres] == "Stres Tinggi").sum()

        rendah_pct = round(rendah / total * 100, 1)
        sedang_pct = round(sedang / total * 100, 1)
        tinggi_pct = round(tinggi / total * 100, 1)

    # =============================
    # MODE BERMAIN
    # =============================

    ranked_pct = classic_pct = brawl_pct = lainnya_pct = 0

    if kolom_mode in df.columns:

        mode = df[kolom_mode].astype(str).str.strip()

        ranked = mode.str.contains("Ranked", case=False).sum()
        classic = mode.str.contains("Classic", case=False).sum()
        brawl = mode.str.contains("Brawl", case=False).sum()

        lainnya = total - ranked - classic - brawl

        ranked_pct = round(ranked / total * 100, 1)
        classic_pct = round(classic / total * 100, 1)
        brawl_pct = round(brawl / total * 100, 1)
        lainnya_pct = round(lainnya / total * 100, 1)

    # =============================
    # FEATURE IMPORTANCE
    # =============================

    feature_importance = []

    nama_fitur = [
        "Usia",
        "Jenis Kelamin",
        "Status",
        "Durasi Bermain",
        "Frekuensi Bermain",
        "Waktu Bermain",
        "Win Rate",
        "Kekalahan Beruntun",
        "Orientasi Bermain",
        "Mode Bermain",
        "Cara Bermain",
        "Rank"
    ]

    if hasattr(model, "feature_importances_"):

        for nama, nilai in zip(
            nama_fitur,
            model.feature_importances_
        ):

            feature_importance.append({
                "nama": nama,
                "pct": round(nilai * 100, 2)
            })

        feature_importance = sorted(
            feature_importance,
            key=lambda x: x["pct"],
            reverse=True
        )

    return render_template(
        "dataset.html",
        total=total,
        badge="Responden",
        jumlah_provinsi=jumlah_provinsi,

        rendah_pct=rendah_pct,
        sedang_pct=sedang_pct,
        tinggi_pct=tinggi_pct,

        ranked_pct=ranked_pct,
        classic_pct=classic_pct,
        brawl_pct=brawl_pct,
        lainnya_pct=lainnya_pct,

        wilayah_data=wilayah_data,
        feature_importance=feature_importance
    )

@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)