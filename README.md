# Truyenfree Scraper

Công cụ cào dữ liệu truyện từ các trang web [truyenfree.org](https://truyenfree.org), [tangthuvien.org](https://tangthuvien.org), [vietnamthuquan.eu](http://vietnamthuquan.eu), [webnovel.com](https://www.webnovel.com), [ntruyen.xyz](https://ntruyen.xyz) và [truyenhoangdung.xyz](https://www.truyenhoangdung.xyz), hỗ trợ vượt qua các cơ chế chống cào dữ liệu và tự động xuất ra định dạng sách điện tử **EPUB** chuyên nghiệp.

---

## Mục tiêu

- Lấy nội dung từng chương của truyện trên các website được hỗ trợ.
- Tự động vượt qua các cơ chế bảo vệ nội dung tương ứng của từng trang.
- Hỗ trợ đi qua Proxy cho các trang yêu cầu (như truyenfree).
- Đóng gói kết quả thành file văn bản `.txt` và xuất thành tệp sách `.epub` hoàn thiện.

---

## Các Nguồn Hỗ Trợ & Cơ Chế Xử Lý

### 1. `truyenfree` — truyenfree.org (Bảo vệ cao)
- **Kỹ thuật bảo vệ**: Chia từng câu/đoạn văn thành hàng trăm thẻ `<span>` nhỏ sắp xếp ngẫu nhiên trong DOM, dùng CSS (`position`, `order`, `transform`...) để hiển thị đúng thứ tự trực quan. Ngoài ra chèn các đoạn text ẩn (trap text) với `display: none` hoặc `opacity: 0`.
- **Giải pháp**: Sử dụng **Playwright** (trình duyệt headless) để kết xuất trang, thu thập tất cả text node trong `<article>`, lọc bỏ phần tử ẩn, lấy **tọa độ hiển thị thực tế** (`getBoundingClientRect`) và sắp xếp lại theo thứ tự hiển thị.
- **Yêu cầu**: Cần cấu hình Proxy. Tốc độ: ~10–30 giây/chương.

### 2. `tangthuvien` — tangthuvien.org (Nhanh)
- **Kỹ thuật**: Next.js SSR — nội dung render sẵn trong HTML ban đầu, không bị xáo trộn.
- **Giải pháp**: `urllib` + `html.parser` tiêu chuẩn, không cần trình duyệt headless.
- **Tốc độ**: ~0.5–1 giây/chương.

### 3. `vietnamthuquan` — vietnamthuquan.eu (POST API)
- **Kỹ thuật**: Nội dung chương được tải động qua POST AJAX, yêu cầu session cookie ASP.NET.
- **Giải pháp**: Thiết lập session bằng `CookieJar`, gửi POST request trực tiếp đến endpoint API để lấy nội dung chương.
- **Tốc độ**: ~0.5–1 giây/chương.

### 4. `webnovel` — (nguồn nội bộ)
- **Giải pháp**: Playwright headless với các chiến lược chờ đặc thù.

### 5. `ntruyen` — ntruyen.xyz (API + Playwright)
- **Kỹ thuật**: Nội dung ở dạng Next.js SPA, cần lấy chapter map từ REST API.
- **Giải pháp**: Fetch song song danh sách chương từ API (`/api/novels/{id}/chapters`), xây dựng chapter map, sau đó dùng Playwright để render từng chương.
- **Tốc độ**: ~0.5–1 giây/chương (sau khi tải xong chapter map).

### 6. `truyenhoangdung` — truyenhoangdung.xyz (Nhanh, mới)
- **Kỹ thuật**: Server-side rendering thuần túy — nội dung chương truyện có đầy đủ ngay trong HTML trả về, không cần JavaScript.
- **Giải pháp**: `urllib` đơn giản + regex để trích xuất tiêu đề (từ `<option selected>`) và nội dung (từ `<div id="noidung">`). Không cần Playwright.
- **Tốc độ**: ~0.3–0.8 giây/chương.

---

## Cấu trúc dự án

```text
Truyenfree/
├── scrapers/
│   ├── __init__.py             # Quản lý danh sách nguồn hỗ trợ và factory khởi tạo
│   ├── base.py                 # Lớp cơ sở trừu tượng BaseScraper
│   ├── truyenfree.py           # truyenfree.org (Playwright + Proxy)
│   ├── tangthuvien.py          # tangthuvien.org (urllib + html.parser)
│   ├── vietnamthuquan.py       # vietnamthuquan.eu (urllib + POST session)
│   ├── webnovel.py             # webnovel (Playwright)
│   ├── ntruyen.py              # ntruyen.xyz (API + Playwright)
│   └── truyenhoangdung.py      # truyenhoangdung.xyz (urllib + regex)
├── main.py                     # File điều khiển quy trình chạy chính (cào -> EPUB)
├── make_epub.py                # File sinh sách EPUB từ file text đầu ra
├── Bia.webp                    # Ảnh bìa mặc định cho sách EPUB
├── requirements.txt            # Các thư viện phụ thuộc
├── README.md                   # Tài liệu này
└── Readme.txt                  # Ghi chú các lệnh nhanh
```

---

## Cấu hình & Cài đặt

### Bước 1: Tạo môi trường ảo
Tùy thuộc vào hệ điều hành của bạn, hãy tạo môi trường ảo Python:

```bash
# Trên Windows
python -m venv venv

# Trên macOS / Linux
python3 -m venv venv_mac
```

### Bước 2: Kích hoạt môi trường ảo

```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# macOS / Linux (zsh/bash)
source venv_mac/bin/activate
```

### Bước 3: Cài đặt thư viện
```bash
pip install -r requirements.txt
```
*(Hoặc cài đặt thủ công các thư viện chính: `pip install playwright ebooklib tqdm lxml`)*

### Bước 4: Cài đặt trình duyệt cho Playwright (Chỉ khi cần cào truyenfree / webnovel / ntruyen)
```bash
playwright install chromium
```

### Bước 5: Cấu hình Proxy (Chỉ dành cho truyenfree.org)
Mở file `scrapers/truyenfree.py`, tìm và chỉnh sửa cấu hình proxy mặc định:
```python
self.proxy = kwargs.get("proxy", {
    "server": "http://1.231.81.166:3128"
})
```

---

## Hướng dẫn sử dụng

Chương trình chính sử dụng thư viện `argparse` để phân tích tham số dòng lệnh một cách chuyên nghiệp và linh hoạt.

### Cú pháp cơ bản
```bash
python main.py <chương_bắt_đầu> <chương_kết_thúc> [nguồn_cào]
```
Trong đó `nguồn_cào` mặc định là `truyenfree` nếu không truyền.

**Các nguồn hỗ trợ:** `truyenfree`, `tangthuvien`, `vietnamthuquan`, `webnovel`, `ntruyen`, `truyenhoangdung`

### Tùy chọn (flags)
| Flag | Rút gọn | Mô tả |
|------|---------|-------|
| `--book-id` | `-b` | ID/Slug của truyện trên website |
| `--title` | `-t` | Tiêu đề sách EPUB |
| `--author` | `-a` | Tác giả sách EPUB |
| `--output` | `-o` | Tên tệp EPUB đầu ra (mặc định: `truyen_output.epub`) |

### Ví dụ

#### truyenhoangdung.xyz (không cần Playwright, nhanh nhất)
```bash
# Cào truyện mặc định (ai-bao-han-tu-tien-dich), chương 1 đến 500
python main.py 1 500 truyenhoangdung

# Cào truyện tùy chỉnh
python main.py 1 100 truyenhoangdung \
  --book-id "ai-bao-han-tu-tien-dich" \
  --title "Ai Bảo Hắn Tu Tiên (Dịch)" \
  --author "Tối Bạch Đích Ô Nha" \
  --output AiBaoHanTuTien.epub
```

#### tangthuvien.org
```bash
python main.py 1 3 tangthuvien

python main.py 1 10 tangthuvien \
  --book-id de-nhat-kiem-than \
  --title "Đệ Nhất Kiếm Thần" \
  --author "Thanh Phong" \
  --output truyen_new.epub
```

#### ntruyen.xyz
```bash
python main.py 1 100 ntruyen \
  --book-id ai-bao-han-tu-tien \
  --title "Ai Bảo Hắn Tu Tiên!" \
  --output output.epub
```

#### truyenfree.org (yêu cầu Proxy)
```bash
python main.py 1 10 truyenfree
```

---

## Lưu ý

- **Thời gian tải ước tính theo nguồn:**

  | Nguồn | Tốc độ ước tính | Cần Playwright |
  |-------|----------------|----------------|
  | `truyenhoangdung` | ~0.3–0.8 giây/chương | ❌ Không |
  | `tangthuvien` | ~0.5–1 giây/chương | ❌ Không |
  | `vietnamthuquan` | ~0.5–1 giây/chương | ❌ Không |
  | `ntruyen` | ~0.5–1 giây/chương | ✅ Có |
  | `webnovel` | ~2–5 giây/chương | ✅ Có |
  | `truyenfree` | ~10–30 giây/chương | ✅ Có + Proxy |

- Tự động bỏ qua chương lỗi và tiếp tục tải chương tiếp theo để tránh gián đoạn.
- Chạy lại script sẽ **xóa dữ liệu cũ** của tệp `truyen_output.txt` và ghi lại từ đầu.

