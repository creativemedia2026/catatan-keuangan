import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Pencatatan Keuangan & Anggaran", page_icon="💰", layout="centered")

st.title("💰 Aplikasi Keuangan & Anggaran Pribadi")
st.write("Catat pemasukan dan pengeluaran harianmu dengan mudah, terhubung langsung ke Google Sheets!")

# --- Koneksi ke Google Sheets ---
def get_google_sheet_client():
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

client = get_google_sheet_client()

if client:
    SPREADSHEET_NAME = "Sheet Anggaran"
    
    try:
        sh = client.open(SPREADSHEET_NAME)
    except Exception as e:
        st.error(f"Tidak dapat menemukan file Google Sheets '{SPREADSHEET_NAME}': {e}")
        sh = None

    if sh:
        tz_wib = pytz.timezone('Asia/Jakarta')
        now_wib = datetime.now(tz_wib)

        # 1. Mengambil Kategori Global & Sub-Kategori dari Tab 'Categories'
        category_rows = []
        try:
            cat_sheet = sh.worksheet("Categories")
            category_rows = cat_sheet.get_all_values()[1:] # Skip header
        except Exception as e:
            st.warning(f"Gagal membaca kategori: {e}")

        expense_dict = {} 
        income_dict = {}
        
        for row in category_rows:
            if len(row) >= 3:
                global_cat = row[0].strip()
                sub_cat = row[1].strip()
                cat_type = row[2].strip().lower()
                
                if global_cat:
                    target_dict = income_dict if "pemasukan" in cat_type else expense_dict
                    if global_cat not in target_dict:
                        target_dict[global_cat] = set()
                    if sub_cat:
                        target_dict[global_cat].add(sub_cat)

        if not expense_dict:
            expense_dict = {
                "Transportasi": {"Bensin", "Parkir"},
                "Makanan & Minuman": {"Makan Siang", "Sarapan", "Makan Malam"}
            }
        if not income_dict:
            income_dict = {
                "Pendapatan Utama": {"Gaji"},
                "Lain-lain": {"Other Income", "Transfer Masuk"}
            }

        expense_globals = sorted(list(expense_dict.keys()))
        income_globals = sorted(list(income_dict.keys()))

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
            accounts = ["BCA", "Gopay", "Dana", "Cash", "BPR WM"]
        
        accounts = sorted(accounts)

        # --- Menu Navigasi ---
        menu = st.sidebar.selectbox("Pilih Menu", ["Catat Transaksi Baru", "Lihat Riwayat & Anggaran", "Edit / Hapus Transaksi"])

        if menu == "Catat Transaksi Baru":
            st.header("📝 Input Transaksi Harian")
            
            col_date, col_time = st.columns(2)
            with col_date:
                tgl = st.date_input("Tanggal", now_wib.date())
            with col_time:
                waktu = st.time_input("Jam & Menit", now_wib.time())
            
            tipe_options = ["--Pilih Tipe Transaksi--", "Pengeluaran", "Pemasukan"]
            tipe = st.selectbox("Tipe Transaksi", tipe_options)
            
            global_categories = []
            current_dict = {}
            if tipe == "Pemasukan":
                global_categories = income_globals
                current_dict = income_dict
            elif tipe == "Pengeluaran":
                global_categories = expense_globals
                current_dict = expense_dict

            kategori_global = "--Pilih Kategori--"
            if tipe != "--Pilih Tipe Transaksi--":
                kategori_global = st.selectbox("Kategori Global", ["--Pilih Kategori--"] + global_categories)

            sub_categories_list = []
            if kategori_global != "--Pilih Kategori--":
                sub_categories_list = sorted(list(current_dict.get(kategori_global, set())))

            sub_kategori = "--Tidak Ada / Opsional--"
            if sub_categories_list:
                sub_kategori = st.selectbox("Sub-Kategori (Opsional / Spesifik)", ["--Tidak Ada / Opsional--"] + sub_categories_list)

            with st.form("transaction_form", clear_on_submit=False):
                nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
                akun = st.selectbox("Akun / Sumber Dana", ["--Pilih Akun--"] + accounts)
                catatan = st.text_input("Catatan Tambahan (Opsional)")
                
                submit_button = st.form_submit_button(label="Simpan Transaksi")
                
                if submit_button:
                    if tipe == "--Pilih Tipe Transaksi--":
                        st.warning("⚠️ Silakan pilih Tipe Transaksi terlebih dahulu.")
                    elif kategori_global == "--Pilih Kategori--":
                        st.warning("⚠️ Silakan pilih Kategori Global terlebih dahulu.")
                    elif akun == "--Pilih Akun--":
                        st.warning("⚠️ Silakan pilih Akun / Sumber Dana terlebih dahulu.")
                    elif nominal <= 0:
                        st.warning("⚠️ Nominal harus lebih besar dari 0.")
                    else:
                        try:
                            try:
                                trans_sheet = sh.worksheet("Transactions")
                            except:
                                trans_sheet = sh.add_worksheet(title="Transactions", rows=1000, cols=8)
                                trans_sheet.append_row(["Tanggal", "Jam", "Tipe", "Kategori Global", "Sub-Kategori", "Nominal", "Akun", "Catatan"])
                            
                            sub_val = "" if sub_kategori == "--Tidak Ada / Opsional--" else sub_kategori
                            row_data = [str(tgl), waktu.strftime('%H:%M'), tipe, kategori_global, sub_val, nominal, akun, catatan]
                            trans_sheet.append_row(row_data)
                            st.success(f"✅ Transaksi pada pukul {waktu.strftime('%H:%M')} berhasil dicatat!")
                        except Exception as e:
                            st.error(f"Gagal menyimpan ke Google Sheets: {e}")

        elif menu == "Lihat Riwayat & Anggaran":
            st.header("📊 Ringkasan & Riwayat Transaksi")
            try:
                trans_sheet = sh.worksheet("Transactions")
                data = trans_sheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
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

        elif menu == "Edit / Hapus Transaksi":
            st.header("✏️ Edit atau Hapus Transaksi")
            try:
                trans_sheet = sh.worksheet("Transactions")
                all_values = trans_sheet.get_all_values()
                
                if len(all_values) > 1:
                    header = all_values[0]
                    rows = all_values[1:]
                    
                    # Membuat list pilihan untuk ditampilkan di selectbox (menampilkan nomor baris dan ringkasan isi)
                    row_options = []
                    for idx, r in enumerate(rows, start=2): # Baris di sheets dimulai dari baris ke-2
                        summary = f"Baris {idx} | Tgl: {r[0]} | {r[2]} | {r[3]} | Rp {r[5]}"
                        row_options.append((idx, summary))
                    
                    selected_item = st.selectbox("Pilih Transaksi yang Ingin Diedit/Dihapus", row_options, format_func=lambda x: x[1])
                    
                    if selected_item:
                        target_row_idx = selected_item[0]
                        current_data = trans_sheet.row_values(target_row_idx)
                        
                        st.markdown("---")
                        st.subheader(f"Edit Data (Baris ke-{target_row_idx})")
                        
                        with st.form("edit_form"):
                            edit_tgl = st.date_input("Tanggal", datetime.strptime(current_data[0], "%Y-%m-%d").date() if current_data[0] else now_wib.date())
                            edit_jam = current_data[1] if len(current_data) > 1 else "12:00"
                            edit_tipe = st.selectbox("Tipe Transaksi", ["Pengeluaran", "Pemasukan"], index=0 if current_data[2] == "Pengeluaran" else 1)
                            edit_kat = st.text_input("Kategori Global", value=current_data[3] if len(current_data) > 3 else "")
                            edit_subkat = st.text_input("Sub-Kategori", value=current_data[4] if len(current_data) > 4 else "")
                            edit_nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000, value=int(current_data[5]) if len(current_data) > 5 and current_data[5].isdigit() else 0)
                            edit_akun = st.text_input("Akun", value=current_data[6] if len(current_data) > 6 else "")
                            edit_catatan = st.text_input("Catatan", value=current_data[7] if len(current_data) > 7 else "")
                            
                            col_update, col_delete = st.columns(2)
                            with col_update:
                                update_btn = st.form_submit_button("💾 Perbarui Transaksi")
                            with col_delete:
                                delete_btn = st.form_submit_button("🗑️ Hapus Transaksi")
                            
                            if update_btn:
                                updated_row = [str(edit_tgl), edit_jam, edit_tipe, edit_kat, edit_subkat, str(edit_nominal), edit_akun, edit_catatan]
                                # Update baris di Google Sheets
                                trans_sheet.update(f"A{target_row_idx}:H{target_row_idx}", [updated_row])
                                st.success(f"✅ Transaksi pada baris ke-{target_row_idx} berhasil diperbarui!")
                                st.rerun()
                                
                            if delete_btn:
                                trans_sheet.delete_rows(target_row_idx)
                                st.success(f"🗑️ Transaksi pada baris ke-{target_row_idx} berhasil dihapus!")
                                st.rerun()
                else:
                    st.info("Belum ada data transaksi yang dapat diedit.")
            except Exception as e:
                st.error(f"Gagal memuat data transaksi: {e}")
