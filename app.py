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
# Kita menggunakan Streamlit Secrets untuk menyimpan kunci kredensial Google API secara aman
@st.cache_resource
def init_connection():
    try:
        # Mengambil kredensial dari secrets Streamlit
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets. Pastikan secrets sudah diatur. Error: {e}")
        return None

client = init_connection()

if client:
    # Ganti dengan Nama File Google Sheets kamu jika berbeda
    SPREADSHEET_NAME = "Anggaran" # Sesuaikan dengan judul file Google Sheets kamu
    
    try:
        sh = client.open(SPREADSHEET_NAME)
        
        # Ambil daftar kategori dari Tab 'Categories'
        cat_sheet = sh.worksheet("Categories")
        categories = cat_sheet.col_values(1)[1:] # Ambil baris ke-2 ke bawah (skip header)
        if not categories:
            categories = ["Makan", "Bensin", "Gaji", "Lainnya"]
            
    except Exception as e:
        st.warning(f"Tidak dapat membaca sheet Categories. Menggunakan kategori default. Error: {e}")
        categories = ["Makan", "Bensin", "Gaji", "Tabungan", "Lainnya"]

    # --- Menu Navigasi Sederhana ---
    menu = st.sidebar.selectbox("Pilih Menu", ["Catat Transaksi Baru", "Lihat Riwayat & Anggaran"])

    if menu == "Catat Transaksi Baru":
        st.header("📝 Input Transaksi Harian")
        
        with st.form("transaction_form"):
            tgl = st.date_input("Tanggal", datetime.now())
            tipe = st.selectbox("Tipe Transaksi", ["Pengeluaran", "Pemasukan"])
            kategori = st.selectbox("Kategori", categories)
            nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
            akun = st.selectbox("Akun / Sumber Dana", ["BCA", "Gopay", "Dana", "Cash", "BPR WM", "Lainnya"])
            catatan = st.text_input("Catatan Tambahan (Opsional)")
            
            submit_button = st.form_submit_button(label="Simpan Transaksi")
            
            if submit_button:
                if nominal > 0:
                    try:
                        trans_sheet = sh.worksheet("Transactions")
                        # Format baris: Tanggal, Tipe, Kategori, Nominal, Akun, Catatan
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
                
                # Ringkasan Total
                st.subheader("Ringkasan Singkat")
                if "Tipe" in df.columns and "Nominal" in df.columns:
                    total_exp = df[df["Tipe"] == "Pengeluaran"]["Nominal"].sum()
                    total_inc = df[df["Tipe"] == "Pemasukan"]["Nominal"].sum()
                    st.metric("Total Pemasukan Tercatat", f"Rp {total_inc:,.0f}")
                    st.metric("Total Pengeluaran Tercatat", f"Rp {total_exp:,.0f}")
            else:
                st.info("Belum ada data transaksi yang tercatat.")
        except Exception as e:
            st.info("Belum ada data atau tab 'Transactions' belum dibuat dengan benar.")
