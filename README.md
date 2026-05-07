# Truyenfree Scraper

Công cụ lấy dữ liệu text truyện từ [truyenfree.org](https://truyenfree.org), hỗ trợ vượt qua cơ chế chống lấy dữ liệu (CSS scrambling) và sử dụng proxy HTTP.

---

## Mục tiêu

- Lấy nội dung từng chapter của truyện trên truyenfree.org
- Vượt qua cơ chế bảo vệ nội dung (ký tự bị xáo trộn bằng CSS)
- Toàn bộ request đi qua proxy HTTP
- Kết quả lưu ra file text có cấu trúc theo yêu cầu

---

## Cơ chế chống scraping và cách xử lý

### Website dùng kỹ thuật gì?

Truyenfree.org chia từng câu/đoạn văn thành hàng trăm `<span>` nhỏ, sắp xếp chúng **ngẫu nhiên trong DOM** nhưng dùng CSS (`position: absolute`, `order`, `transform`...) để hiển thị đúng thứ tự trên màn hình. Nếu đọc thẳng từ HTML, kết quả sẽ là chuỗi ký tự lộn xộn.

Ngoài ra, website còn chèn các đoạn **text ẩn** (watermark/trap text) với `display: none` hoặc `opacity: 0` để đánh dấu nội dung bị sao chép.

### Giải pháp

Sử dụng **Playwright** (trình duyệt headless) để render trang web thật sự, sau đó:

1. Thu thập tất cả text node có trong `<article>` (container nội dung)
2. Lọc bỏ các element **ẩn** (`display: none`, `visibility: hidden`, `opacity: 0`, kích thước = 0)
3. Lọc bỏ text watermark đã biết
4. Lấy **tọa độ hiển thị thực tế** (`getBoundingClientRect`) của từng text node
5. Sắp xếp theo thứ tự `top → left` (trên xuống dưới, trái qua phải)
6. Ghép lại thành đoạn văn liên mạch với logic:
   - `vGap > 1.5 × lineHeight` → xuống đoạn mới (`\n`)
   - `vGap > 0.5 × lineHeight` → text wrap dòng, thêm dấu cách
   - `hGap > 4px` → khoảng cách từ cùng dòng, thêm dấu cách
   - Còn lại → ký tự scrambled liền nhau, không thêm gì

---

## Cấu trúc dự án

```
Truyenfree/
├── venv/               # Môi trường ảo Python (không commit)
├── scraper.py          # Script cào dữ liệu
├── make_epub.py        # Script chuyển đổi text sang EPUB
├── main.py             # Script chạy toàn bộ quy trình (Cào -> EPUB)
├── truyen_output.txt   # File text tạm thời
├── truyen_output.epub  # File EPUB kết quả
├── README.md           # Tài liệu này
└── Readme.txt          # Ghi chú lệnh nhanh
```

---

## Yêu cầu hệ thống

- Python **3.8+**
- Windows / Linux / macOS
- Kết nối internet (qua proxy hoặc trực tiếp)

---

## Cài đặt

### Bước 1: Tạo môi trường ảo

```powershell
cd "e:\Code\Code Python\Truyenfree"
python -m venv venv
```

### Bước 2: Kích hoạt môi trường ảo

```powershell
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# Linux / macOS
source venv/bin/activate
```

### Bước 3: Cài đặt thư viện

```powershell
pip install playwright ebooklib
```

### Bước 4: Cài đặt trình duyệt Chromium cho Playwright

```powershell
playwright install chromium
```

---

## Cấu hình proxy

Mở file `scraper.py`, tìm và chỉnh sửa:

```python
proxy = {
    "server": "http://1.231.81.166:3128"
}
```

---

## Sử dụng

Để chạy toàn bộ quy trình từ lúc lấy dữ liệu đến khi xuất file EPUB:

```powershell
python main.py <chapter_bắt_đầu> <chapter_kết_thúc>
```

### Ví dụ

```powershell
# Lấy và tạo EPUB cho chapter 1 đến 10
python main.py 1 10
```

### Chạy lẻ từng bước (nếu cần)

1. **Chỉ cào dữ liệu:** `python scraper.py 1 10`
2. **Chỉ tạo EPUB:** `python make_epub.py`

### Kết quả

- File text tạm: `truyen_output.txt`
- File EPUB hoàn thiện: `truyen_output.epub`

**Quy tắc định dạng EPUB:**
- Hỗ trợ hiển thị tiếng Việt UTF-8 (NFC) chuẩn.
- Đã fix lỗi font và dấu bị lệch (sử dụng font hệ thống hỗ trợ tiếng Việt).
- Mục lục tự động tạo theo danh sách chương.

**Quy tắc định dạng:**
- `<h1>` — Tên chapter
- `<h2>` — Toàn bộ nội dung chapter (text liên mạch, xuống dòng theo đoạn văn)

---

## Lưu ý

- Mỗi chapter mất khoảng **10–30 giây** để tải (phụ thuộc tốc độ proxy)
- Script tự động nghỉ **1 giây** giữa các chapter để tránh bị chặn
- Nếu một chapter thất bại, script sẽ **bỏ qua và tiếp tục** chapter tiếp theo
- Chạy lại script sẽ **xoá file cũ** và tạo mới từ đầu

---

## URL truyện

```
https://truyenfree.org/truyen/dich-quang-am-chi-ngoai
```

Pattern URL từng chapter:

```
https://truyenfree.org/truyen/dich-quang-am-chi-ngoai/chuong-{số}
```
