import sys
import asyncio
import argparse
from make_epub import make_epub
from scrapers import get_scraper, SUPPORTED_SOURCES

async def run_pipeline(start_ch, end_ch, source, book_id, book_title, book_author, output_epub):
    output_txt = "truyen_output.txt"
    
    print(f"--- BẮT ĐẦU QUY TRÌNH ({source.upper()}): {book_title} ({start_ch} -> {end_ch}) ---")
    
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
    parser = argparse.ArgumentParser(description="Công cụ cào truyện và đóng gói EPUB chuyên nghiệp.")
    parser.add_argument("start", type=int, help="Chương bắt đầu")
    parser.add_argument("end", type=int, help="Chương kết thúc")
    # Sử dụng nargs="?" để giữ cú pháp cũ: main.py <start> <end> [source]
    parser.add_argument("source", nargs="?", default="truyenfree", choices=SUPPORTED_SOURCES,
                        help="Nguồn cào truyện (mặc định: truyenfree)")
    
    parser.add_argument("--book-id", "-b", help="Slug/ID của truyện trên website")
    parser.add_argument("--title", "-t", help="Tiêu đề sách EPUB")
    parser.add_argument("--author", "-a", help="Tác giả sách EPUB")
    parser.add_argument("--output", "-o", default="truyen_output.epub", help="File EPUB đầu ra (mặc định: truyen_output.epub)")
    
    args = parser.parse_args()
    
    # Thiết lập cấu hình mặc định dựa trên nguồn cào
    source = args.source.lower()
    book_id = args.book_id
    title = args.title
    author = args.author
    
    if source == "tangthuvien":
        if not book_id:
            book_id = "de-nhat-kiem-than"
        if not title:
            title = "[Dịch] Đệ Nhất Kiếm Thần"
        if not author:
            author = "Thanh Phong"
    elif source == "vietnamthuquan":
        if not book_id:
            book_id = "2qtqv3m3237n1n2nqntntn31n343tq83a3q3m3237nvn"
        if not title:
            title = "[Dịch] Đệ Nhất Kiếm Thần"
        if not author:
            author = "Thanh Phong"
    elif source == "webnovel":
        if not book_id:
            book_id = "ai-bao-han-tu-tien"
        if not title:
            title = "Ai Bảo Hắn Tu Tiên!"
        if not author:
            author = "Tối Bạch Đích Ô Nha"
    elif source == "ntruyen":
        if not book_id:
            book_id = "ai-bao-han-tu-tien"
        if not title:
            title = "Ai Bảo Hắn Tu Tiên!"
        if not author:
            author = "Tối Bạch Đích Ô Nha"
    elif source == "truyenhoangdung":
        if not book_id:
            book_id = "ai-bao-han-tu-tien-dich"
        if not title:
            title = "Ai Bảo Hắn Tu Tiên (Dịch)"
        if not author:
            author = "Tối Bạch Đích Ô Nha"
    else: # truyenfree
        if not book_id:
            book_id = "dich-linh-canh-hanh-gia"
        if not title:
            title = "[Dịch] Quang Âm Chi Ngoại"
        if not author:
            author = "Nhĩ Căn"
            
    asyncio.run(run_pipeline(args.start, args.end, source, book_id, title, author, args.output))

if __name__ == "__main__":
    main()


