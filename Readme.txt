# === KÍCH HOẠT MÔI TRƯỜNG ===
source venv_mac/bin/activate

# === TỰ ĐỘNG NHẬN BIẾT LINK TRUYỆN (KHÔNG CẦN CHỌN TRANG) ===
python3 main.py https://www.tvtruyen.cc/he-thong-manh-nhat-dich.html 1 100
python3 main.py 1 100 https://ntruyen.xyz/truyen/ai-bao-han-tu-tien
python3 main.py 1 100 -b https://www.truyenhoangdung.xyz/ai-bao-han-tu-tien-dich/

# === CÁC CÚ PHÁP CŨ (VẪN HỖ TRỢ) ===
# === TRUYENHOANGDUNG.XYZ ===
python3 main.py 1 100 truyenhoangdung
python3 main.py 70 1000 truyenhoangdung -t "Ai Bảo Hắn Tu Tiên (Dịch)" -o AiBaoHanTuTien.epub

# === NTRUYEN.XYZ ===
python3 main.py 1 100 ntruyen

# === TANGTHUVIEN.ORG ===
python3 main.py 1 10 tangthuvien

# === TRUYENFREE.ORG (cần Proxy) ===
python3 main.py 1 10 truyenfree

# === TVTRUYEN.CC (cần Proxy) ===
python3 main.py 1 10 tvtruyen

# === GIT ===
git add .
git commit -m "mô tả"
git push