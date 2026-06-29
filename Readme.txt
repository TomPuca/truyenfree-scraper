# === KÍCH HOẠT MÔI TRƯỜNG ===
source venv_mac/bin/activate

# === TRUYENHOANGDUNG.XYZ (nhanh nhất, không cần Playwright) ===
python3 main.py 1 100 truyenhoangdung
python3 main.py 70 1000 truyenhoangdung -t "Ai Bảo Hắn Tu Tiên (Dịch)" -o AiBaoHanTuTien.epub

# === NTRUYEN.XYZ ===
python3 main.py 1 100 ntruyen
python3 main.py 1 100 ntruyen -b ai-bao-han-tu-tien -t "Ai Bảo Hắn Tu Tiên!" -o output.epub

# === TANGTHUVIEN.ORG ===
python3 main.py 1 10 tangthuvien
python3 main.py 1 10 tangthuvien -b de-nhat-kiem-than -t "Đệ Nhất Kiếm Thần" -a "Thanh Phong" -o truyen_new.epub

# === TRUYENFREE.ORG (cần Proxy) ===
python3 main.py 1 10 truyenfree

# === GIT ===
git add .
git commit -m "mô tả"
git push