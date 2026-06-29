import urllib.request
import urllib.parse
import http.cookiejar
import re
import os
import time
import html as html_lib
import asyncio
from tqdm import tqdm
from scrapers.base import BaseScraper

class VietnamThuQuanScraper(BaseScraper):
    def __init__(self, book_id, **kwargs):
        # book_id ở đây chính là tid (ví dụ: '2qtqv3m3237n1n2nqntntn31n343tq83a3q3m3237nvn')
        super().__init__(book_id, **kwargs)
        self.main_url = f"http://vietnamthuquan.eu/truyen/truyen.aspx?tid={self.book_id}"
        self.post_url = "http://vietnamthuquan.eu/truyen/chuonghoi_moi.aspx"
        
        # Khởi tạo cookie jar để lưu trữ và gửi cookie (tránh vòng lặp redirect 302 của ASP.NET)
        self.cookie_jar = http.cookiejar.CookieJar()
        self.cookie_processor = urllib.request.HTTPCookieProcessor(self.cookie_jar)
        self.opener = urllib.request.build_opener(self.cookie_processor)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

    def _establish_session(self):
        """Truy cập trang chính để lấy session cookie và tìm tuaid"""
        try:
            req = urllib.request.Request(self.main_url, headers=self.headers)
            with self.opener.open(req, timeout=20) as response:
                html_content = response.read().decode('utf-8')
                
                # Tìm tuaid trong mã nguồn HTML (ví dụ: tuaid=24755)
                match = re.search(r'tuaid=(\d+)', html_content)
                if match:
                    tuaid = match.group(1)
                    return tuaid
                else:
                    raise ValueError("Không tìm thấy tham số 'tuaid' trên trang sách.")
        except Exception as e:
            print(f"Lỗi khi thiết lập phiên làm việc với vietnamthuquan.eu: {e}")
            raise

    def _fetch_chapter_sync(self, tuaid, chuong_id, retries=3):
        """Gửi POST request để lấy nội dung chương truyện (đồng bộ)"""
        data = {
            "tuaid": tuaid,
            "chuongid": str(chuong_id)
        }
        payload = urllib.parse.urlencode(data).encode('utf-8')
        
        # Thiết lập header đặc thù cho POST AJAX
        headers = self.headers.copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = self.main_url
        
        for attempt in range(retries):
            try:
                req = urllib.request.Request(self.post_url, data=payload, headers=headers, method="POST")
                with self.opener.open(req, timeout=15) as response:
                    html_response = response.read().decode('utf-8')
                    parts = html_response.split("--!!tach_noi_dung!!--")
                    
                    if len(parts) >= 4:
                        # 1. Trích xuất số chương (ví dụ: Chương 1) từ parts[3]
                        chapter_number_match = re.search(r'<h1>(Chương \d+)', parts[3])
                        chapter_number = chapter_number_match.group(1).strip() if chapter_number_match else f"Chương {chuong_id}"
                        
                        # 2. Trích xuất tiêu đề phụ từ parts[1]
                        subtitle_match = re.search(r'class="tuahoi1">(.*?)</span>', parts[1])
                        subtitle = subtitle_match.group(1).strip() if subtitle_match else ""
                        
                        # Khớp tiêu đề đầy đủ
                        if subtitle:
                            # Viết hoa chữ cái đầu cho tiêu đề phụ đẹp mắt
                            subtitle = subtitle[0].upper() + subtitle[1:] if len(subtitle) > 1 else subtitle.upper()
                            full_title = f"{chapter_number}: {subtitle}"
                        else:
                            full_title = chapter_number
                            
                        # 3. Trích xuất nội dung từ parts[2]
                        content_html = parts[2]
                        
                        # Xoá HTML tags và giải mã HTML entities
                        clean_text = re.sub(r'<[^>]+>', '\n', content_html)
                        clean_text = html_lib.unescape(clean_text)
                        
                        # Loại bỏ toàn bộ các dòng trống
                        lines = []
                        for line in clean_text.split('\n'):
                            line = line.strip()
                            if line:
                                lines.append(line)
                        
                        content = "\n".join(lines)
                        return full_title, content
            except Exception as e:
                if attempt == retries - 1:
                    print(f"\nLỗi cào chương {chuong_id} (thử lại {attempt+1}/{retries}): {e}")
                time.sleep(1)
                
        return None, None

    async def _fetch_chapter_async(self, loop, tuaid, chuong_id):
        return await loop.run_in_executor(None, self._fetch_chapter_sync, tuaid, chuong_id)

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        loop = asyncio.get_running_loop()
        
        # 1. Thiết lập session và lấy tuaid
        print("Đang kết nối tới vietnamthuquan.eu để thiết lập phiên...")
        try:
            tuaid = self._establish_session()
            print(f"Kết nối thành công! Mã ID truyện (tuaid): {tuaid}")
        except Exception:
            return False
            
        # Xoá file cũ nếu tồn tại
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            
        success_count = 0
        failed = []
        
        print(f"Bắt đầu tải từ vietnamthuquan.eu: Chương {start} đến {end}")
        
        with tqdm(total=total, desc="Scraping VNTQ", unit="chap",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            for i in range(start, end + 1):
                pbar.set_postfix_str(f"ch.{i}")
                
                title, content = await self._fetch_chapter_async(loop, tuaid, i)
                
                if title and content:
                    with open(self.output_file, "a", encoding="utf-8") as f:
                        f.write(f"<h1>{title}</h1>\n")
                        f.write(f"<h2>{content}</h2>\n\n")
                    success_count += 1
                    pbar.set_postfix_str(title[:40])
                else:
                    failed.append(i)
                    pbar.set_postfix_str(f"ch.{i} FAILED")
                    
                pbar.update(1)
                # Sleep nhẹ 0.4s giữa các chương
                await asyncio.sleep(0.4)
                
        print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
        if failed:
            print(f"Thất bại ({len(failed)} chương): {failed}")
            
        return success_count > 0
