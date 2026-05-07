import sys
import asyncio
from scraper import main as scrape_main
from make_epub import make_epub

async def run_pipeline(start_ch, end_ch):
    output_txt = "truyen_output.txt"
    output_epub = "truyen_output.epub"
    
    print(f"--- BẮT ĐẦU QUY TRÌNH: CHAPTER {start_ch} ĐẾN {end_ch} ---")
    
    # 1. Chạy Scraper
    print("\n[1/2] Đang lấy dữ liệu từ website...")
    try:
        await scrape_main(start_ch, end_ch)
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu: {e}")
        return

    # 2. Chạy EPUB Converter
    print(f"\n[2/2] Đang chuyển đổi sang EPUB...")
    try:
        make_epub(output_txt, output_epub, "[Dịch] Quang Âm Chi Ngoại", "Nhĩ Căn")
    except Exception as e:
        print(f"Lỗi khi tạo EPUB: {e}")
        return

    print(f"\n--- HOÀN TẤT ---")
    print(f"Kết quả lưu tại: {output_epub}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Cú pháp: python main.py <chapter_đầu> <chapter_cuối>")
        sys.exit(1)
    
    start_ch = int(sys.argv[1])
    end_ch = int(sys.argv[2])
    
    asyncio.run(run_pipeline(start_ch, end_ch))
