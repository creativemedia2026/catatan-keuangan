import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Pencatatan Keuangan & Anggaran", page_icon="💰", layout="centered")

st.title("💰 Aplikasi Keuangan & Anggaran Pribadi")
st.write("Catat pemasukan dan pengeluaran harianmu dengan mudah, terhubung langsung ke Google Sheets!")

# --- Koneksi ke Google Sheets ---
@st.cache_resource
def init_connection():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets: {e}")
        return None

client = init_connection()

if client:
    SPREADSHEET_NAME = "Anggaran" # Pastikan judul file Google Sheets kamu sesuai
    
    try:
        sh = client.open(SPREADSHEET_NAME)
    except Exception as e:
        st.error(f"Tidak dapat menemukan file Google Sheets '{SPREADSHEET_NAME}': {e}")
        sh = None

    if sh:
        # Mengambil kategori secara dinamis dari Tab 'Categories' di Google Sheets
        categories = []
        try:
            cat_sheet = sh.worksheet("Categories")
            # Mengambil seluruh nilai di Kolom A
            raw_cats = cat_sheet.col_values(1)
            # Membersihkan data kosong dan mengabaikan baris pertama jika itu judul (header)
            if len(raw_cats) > 1:
                categories = [cat.strip() for cat in raw_cats[1:] if cat.strip()]
            elif len(raw_cats) == 1:
                categories = [raw_cats[0].strip()]
        except Exception:
            pass
        
        # Jika sheet Categories kosong atau belum ada, gunakan cadangan default
        if not categories:
            categories = [
                "Gaji", "Persepuluhan", "Tabungan BPR WM", "Netflix", 
                "Paketan Smartfren", "Pulsa Indosat", "Paket Internet XL", 
                "Google Play", "TF BCA", "Topup Dana", "Topup Gopay", 
                "Topup Flip", "BPJS", "Bensin", "Topup Flazz BCA", 
                "Topup E-Money Mandiri", "Iuran Piknik", "Tabungan Emas Pegadaian", 
                "Anggaran Makan", "Lainnya"
            ]

        # --- Menu Navigasi ---
        menu = st.sidebar.selectbox("Pilih Menu", ["Catat Transaksi Baru", "Lihat Riwayat & Anggaran"])

        if menu == "Catat Transaksi Baru":
            st.header("📝 Input Transaksi Harian")
            
            with st.form("transaction_form", clear_on_submit=True):
                tgl = st.date_input("Tanggal", datetime.now())
                tipe = st.selectbox("Tipe Transaksi", ["Pengeluaran", "Pemasukan"])
                kategori = st.selectbox("Kategori (Otomatis dari Google Sheets)", categories)
                nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
                akun = st.selectbox("Akun / Sumber Dana", ["BCA", "Gopay", "Dana", "Cash", "BPR WM", "Lainnya"])
                catatan = st.text_input("Catatan Tambahan (Opsional)")
                
                submit_button = st.form_submit_button(label="Simpan Transaksi")
                
                if submit_button:
                    if nominal > 0:
                        try:
                            # Coba ambil atau buat tab 'Transactions' otomatis jika belum ada
                            try:
                                trans_sheet = sh.worksheet("Transactions")
                            except:
                                trans_sheet = sh.add_worksheet(title="Transactions", rows=1000, cols=6)
                                trans_sheet.append_row(["Tanggal", "Tipe", "Kategori", "Nominal", "Akun", "Catatan"])
                            
                            row_data = [str(tgl), tipe, kategori, nominal, akun, catatan]
                            trans_sheet.append_row(row_data)
                            st.success("✅ Transaksi berhasil dicatat dan dikirim ke Google Sheets!")
                        except Exception as e:
                            st.error(f"Gagal menyimpan ke Google Sheets: {e}")
                    else:
                        st.warning("⚠️ Nominal harus lebih besar dari 0.")

        elif menu == "Lihat Riwayat & Anggaran":
            st.header("📊 Ringkasan & Riwayat Transaksi")
            try:
                trans_sheet = sh.worksheet("Transactions")
                data = trans_sheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    st.subheader("Ringkasan Singkat")
                    if "Tipe" in df.columns and "Nominal" in df.columns:
                        total_exp = df[df["Tipe"] == "Pengeluaran"]["Nominal"].sum()
                        total_inc = df[df["Tipe"] == "Pemasukan"]["Nominal"].sum()
                        st.metric("Total Pemasukan Tercatat", f"Rp {total_inc:,.0f}")
                        st.metric("Total Pengeluaran Tercatat", f"Rp {total_exp:,.0f}")
                else:
                    st.info("Belum ada data transaksi yang tercatat.")
            except Exception as e:
                st.info("Belum ada data atau tab 'Transactions' belum tersedia.")
