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
    SPREADSHEET_NAME = "Sheet Anggaran"
    
    try:
        sh = client.open(SPREADSHEET_NAME)
    except Exception as e:
        st.error(f"Tidak dapat menemukan file Google Sheets '{SPREADSHEET_NAME}': {e}")
        sh = None

    if sh:
        # 1. Mengambil Kategori Berdasarkan Tipe dari Tab 'Categories'
        category_data = []
        try:
            cat_sheet = sh.worksheet("Categories")
            # Mengambil semua baris sebagai list of dict atau records
            category_data = cat_sheet.get_all_records()
        except Exception:
            pass

        # Fallback jika sheet categories belum memiliki Kolom Tipe
        if not category_data:
            category_data = [
                {"Kategori": "Gaji", "Tipe": "Pemasukan"},
                {"Kategori": "Bensin", "Tipe": "Pengeluaran"},
                {"Kategori": "Anggaran Makan", "Tipe": "Pengeluaran"},
                {"Kategori": "Persepuluhan", "Tipe": "Pengeluaran"}
            ]

        # 2. Mengambil Daftar Akun dari Tab 'Accounts'
        accounts = []
        try:
            acc_sheet = sh.worksheet("Accounts")
            raw_accs = acc_sheet.col_values(1)
            if len(raw_accs) > 1:
                accounts = [acc.strip() for acc in raw_accs[1:] if acc.strip()]
        except Exception:
            pass
        
        if not accounts:
            accounts = ["BCA", "Gopay", "Dana", "Cash", "BPR WM", "Lainnya"]

        # --- Menu Navigasi ---
        menu = st.sidebar.selectbox("Pilih Menu", ["Catat Transaksi Baru", "Lihat Riwayat & Anggaran"])

        if menu == "Catat Transaksi Baru":
            st.header("📝 Input Transaksi Harian")
            
            with st.form("transaction_form", clear_on_submit=True):
                tgl = st.date_input("Tanggal", datetime.now())
                
                # Pilihan Tipe Transaksi
                tipe = st.selectbox("Tipe Transaksi", ["Pengeluaran", "Pemasukan"])
                
                # Filter kategori secara dinamis berdasarkan Tipe yang dipilih
                filtered_categories = [
                    row["Kategori"] for row in category_data 
                    if str(row.get("Tipe", "")).strip().lower() == tipe.lower()
                ]
                
                if not filtered_categories:
                    filtered_categories = [row["Kategori"] for row in category_data] # Cadangan jika kolom tipe kosong

                kategori = st.selectbox("Kategori", filtered_categories)
                nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
                akun = st.selectbox("Akun / Sumber Dana", accounts)
                catatan = st.text_input("Catatan Tambahan (Opsional)")
                
                submit_button = st.form_submit_button(label="Simpan Transaksi")
                
                if submit_button:
                    if nominal > 0:
                        try:
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
                    
                    # Ringkasan Total
                    st.subheader("Ringkasan Total")
                    if "Tipe" in df.columns and "Nominal" in df.columns:
                        total_exp = df[df["Tipe"] == "Pengeluaran"]["Nominal"].sum()
                        total_inc = df[df["Tipe"] == "Pemasukan"]["Nominal"].sum()
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Pemasukan", f"Rp {total_inc:,.0f}")
                        with col2:
                            st.metric("Total Pengeluaran", f"Rp {total_exp:,.0f}")
                else:
                    st.info("Belum ada data transaksi yang tercatat.")
            except Exception as e:
                st.info("Belum ada data atau tab 'Transactions' belum tersedia.")

            # --- Bagian Rekap Anggaran Bulanan dari Tab 'Anggaran' ---
            st.markdown("---")
            st.header("🎯 Rekap Tab Anggaran Bulanan")
            try:
                anggaran_sheet = sh.worksheet("Anggaran")
                anggaran_data = anggaran_sheet.get_all_records()
                if anggaran_data:
                    df_anggaran = pd.DataFrame(anggaran_data)
                    st.dataframe(df_anggaran, use_container_width=True)
                else:
                    st.info("Tab 'Anggaran' kosong.")
            except Exception as e:
                st.info("Memuat rekap anggaran...")
