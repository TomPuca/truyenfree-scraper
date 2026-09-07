import sys
import asyncio
import argparse
import re
from make_epub import make_epub
from scrapers import get_scraper, detect_source_and_book_id, SUPPORTED_SOURCES

def get_defaults_for_source_and_book(source: str, book_id: str):
    """
    Trả về (title, author, default_output) mặc định tương ứng với source và book_id.
    """
    presets = {
        "he-thong-manh-nhat-dich": ("[Dịch] Hệ Thống Mạnh Nhất", "Tân Phong", "HeThongManhNhat.epub"),
        "ai-bao-han-tu-tien": ("Ai Bảo Hắn Tu Tiên!", "Tối Bạch Đích Ô Nha", "AiBaoHanTuTien.epub"),
        "ai-bao-han-tu-tien-dich": ("Ai Bảo Hắn Tu Tiên (Dịch)", "Tối Bạch Đích Ô Nha", "AiBaoHanTuTien.epub"),
        "de-nhat-kiem-than": ("[Dịch] Đệ Nhất Kiếm Thần", "Thanh Phong", "DeNhatKiemThan.epub"),
        "dich-linh-canh-hanh-gia": ("[Dịch] Linh Cảnh Hành Giả", "Cừu Thổ", "LinhCanhHanhGia.epub"),
        "2qtqv3m3237n1n2nqntntn31n343tq83a3q3m3237nvn": ("[Dịch] Đệ Nhất Kiếm Thần", "Thanh Phong", "DeNhatKiemThan.epub")
    }

    if book_id in presets:
        return presets[book_id]

    source_defaults = {
        "tvtruyen": ("Hệ Thống Mạnh Nhất (Dịch)", "Tân Phong", "HeThongManhNhat.epub"),
        "ntruyen": ("Ai Bảo Hắn Tu Tiên!", "Tối Bạch Đích Ô Nha", "AiBaoHanTuTien.epub"),
        "truyenhoangdung": ("Ai Bảo Hắn Tu Tiên (Dịch)", "Tối Bạch Đích Ô Nha", "AiBaoHanTuTien.epub"),
        "tangthuvien": ("[Dịch] Đệ Nhất Kiếm Thần", "Thanh Phong", "DeNhatKiemThan.epub"),
        "vietnamthuquan": ("[Dịch] Đệ Nhất Kiếm Thần", "Thanh Phong", "DeNhatKiemThan.epub"),
        "webnovel": ("Ai Bảo Hắn Tu Tiên!", "Tối Bạch Đích Ô Nha", "AiBaoHanTuTien.epub"),
        "truyenfull": ("Truyện Full", "Unknown", "truyen_output.epub"),
        "truyenfree": ("[Dịch] Quang Âm Chi Ngoại", "Nhĩ Căn", "truyen_output.epub")
    }

    if book_id:
        clean_slug = book_id.replace(".html", "").replace("_", "-")
        words = []
        for word in clean_slug.split("-"):
            if word.lower() == "dich":
                words.append("(Dịch)")
            else:
                words.append(word.capitalize())
        
        auto_title = " ".join(words)
        filename_parts = [w for w in words if w not in ("(Dịch)", "Dich")]
        auto_output = ("".join(filename_parts) if filename_parts else "output") + ".epub"
        return auto_title, "Unknown", auto_output

    return source_defaults.get(source, ("Truyện Hay", "Unknown", "output.epub"))


def parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Công cụ cào truyện và đóng gói EPUB tự động nhận biết link truyện."
    )
    parser.add_argument("arg1", nargs="?", default=None, help="Link truyện HOẶC Chương bắt đầu (VD: 1 hoặc https://...)")
    parser.add_argument("arg2", nargs="?", default=None, help="Chương kết thúc HOẶC Chương bắt đầu")
    parser.add_argument("arg3", nargs="?", default=None, help="Nguồn cào HOẶC Link truyện HOẶC Chương kết thúc")

    parser.add_argument("--book-id", "-b", "--url", "-u", dest="book_id", help="Link truyện hoặc Slug/ID của truyện")
    parser.add_argument("--title", "-t", help="Tiêu đề sách EPUB")
    parser.add_argument("--author", "-a", help="Tác giả sách EPUB")
    parser.add_argument("--output", "-o", help="File EPUB đầu ra")

    args = parser.parse_args()

    positionals = [a for a in [args.arg1, args.arg2, args.arg3] if a is not None]

    urls_found = []
    nums_found = []
    str_found = []

    for p in positionals:
        if (p.startswith("http://") or p.startswith("https://") or 
            any(ext in p for ext in ["tvtruyen.cc", "ntruyen.xyz", "truyenhoangdung.xyz", "tangthuvien", "vietnamthuquan", "webnovel", "truyenfree", "truyenfull.live"])):
            urls_found.append(p)
        elif p.isdigit():
            nums_found.append(int(p))
        else:
            str_found.append(p)

    # 1. Start, end
    start = 1
    end = 100
    if len(nums_found) >= 2:
        start, end = nums_found[0], nums_found[1]
    elif len(nums_found) == 1:
        start = nums_found[0]
        end = start

    # 2. Tự động nhận biết link truyện từ positionals hoặc --book-id / --url
    input_url = urls_found[0] if urls_found else args.book_id

    source = None
    book_id = None

    if input_url:
        source, book_id = detect_source_and_book_id(input_url)

    if not source and str_found:
        candidate = str_found[0].lower()
        if candidate in SUPPORTED_SOURCES:
            source = candidate

    if args.book_id and not book_id:
        src, b_id = detect_source_and_book_id(args.book_id)
        if src:
            source = source or src
            book_id = b_id
        else:
            book_id = args.book_id

    if not source:
        source = "tvtruyen"

    def_title, def_author, def_output = get_defaults_for_source_and_book(source, book_id)

    title = args.title if args.title else def_title
    author = args.author if args.author else def_author
    output = args.output if args.output else def_output

    if not book_id:
        if source == "tangthuvien":
            book_id = "de-nhat-kiem-than"
        elif source == "vietnamthuquan":
            book_id = "2qtqv3m3237n1n2nqntntn31n343tq83a3q3m3237nvn"
        elif source in ("webnovel", "ntruyen"):
            book_id = "ai-bao-han-tu-tien"
        elif source == "truyenhoangdung":
            book_id = "ai-bao-han-tu-tien-dich"
        elif source == "tvtruyen":
            book_id = "he-thong-manh-nhat-dich"
        else:
            book_id = "dich-linh-canh-hanh-gia"

    return start, end, source, book_id, title, author, output


async def run_pipeline(start_ch, end_ch, source, book_id, book_title, book_author, output_epub):
    output_txt = "truyen_output.txt"
    
    print(f"--- BẮT ĐẦU QUY TRÌNH ({source.upper()}): {book_title} ({start_ch} -> {end_ch}) ---")
    print(f"Nguồn: {source} | Book ID/Slug: {book_id}")
    
    # 1. Khởi tạo và chạy Scraper
    print("\n[1/2] Đang lấy dữ liệu từ website...")
    try:
        scraper = get_scraper(
            source_name=source,
            book_id=book_id,
            book_title=book_title,
            book_author=book_author,
            output_file=output_txt
        )
        success = await scraper.scrape(start_ch, end_ch)
        if not success:
            print("Cảnh báo: Không có chương nào được cào thành công.")
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu: {e}")
        return

    # 2. Chạy EPUB Converter
    print(f"\n[2/2] Đang chuyển đổi sang EPUB...")
    try:
        make_epub(output_txt, output_epub, book_title, book_author)
    except Exception as e:
        print(f"Lỗi khi tạo EPUB: {e}")
        return

    print(f"\n--- HOÀN TẤT ---")
    print(f"Kết quả lưu tại: {output_epub}")


def main():
    start, end, source, book_id, title, author, output = parse_cli_args()
    asyncio.run(run_pipeline(start, end, source, book_id, title, author, output))


if __name__ == "__main__":
    main()
