import urllib.request
import re
import os
import time
import html as html_lib
import asyncio
from tqdm import tqdm
from scrapers.base import BaseScraper

class WebNovelScraper(BaseScraper):
    def __init__(self, book_id, **kwargs):
        # book_id ở đây chính là slug truyện (ví dụ: 'ai-bao-han-tu-tien')
        super().__init__(book_id, **kwargs)
        self.base_url = "https://webnovel.vn"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

    def _fetch_chapter_sync(self, chuong_id, retries=3):
        """Tải và parse nội dung chương truyện (đồng bộ)"""
        url = f"{self.base_url}/{self.book_id}/chuong-{chuong_id}/"
        
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    html_content = response.read().decode('utf-8')
                    
                    # 1. Trích xuất tiêu đề chương từ <p class="reader__chapter">...</p>
                    title_match = re.search(r'<p class="reader__chapter">(.*?)</p>', html_content)
                    if title_match:
                        title = title_match.group(1).strip()
                    else:
                        title = f"Chương {chuong_id}"
                    
                    # 2. Trích xuất nội dung từ <div id="chapter-c">...</div>
                    content_match = re.search(r'<div id="chapter-c">(.*?)</div>', html_content, re.DOTALL)
                    if not content_match:
                        content_match = re.search(r'<div[^>]*id="chapter-c"[^>]*>(.*?)</div>', html_content, re.DOTALL)
                        
                    if content_match:
                        raw_content = content_match.group(1)
                        # Thay thế <br> và <br/> bằng newline \n
                        clean_content = re.sub(r'<br\s*/?>', '\n', raw_content)
                        # Loại bỏ các tag HTML khác
                        clean_content = re.sub(r'<[^>]+>', '', clean_content)
                        # Giải mã HTML entities
                        clean_content = html_lib.unescape(clean_content)
                        
                        # Loại bỏ toàn bộ các dòng trống
                        lines = []
                        for line in clean_content.split('\n'):
                            line = line.strip()
                            if line:
                                lines.append(line)
                        
                        content = "\n".join(lines)
                        return title, content
            except Exception as e:
                if attempt == retries - 1:
                    print(f"\nLỗi cào chương {chuong_id} (thử lại {attempt+1}/{retries}): {e}")
                time.sleep(1)
                
        return None, None

    async def _fetch_chapter_async(self, loop, chuong_id):
        return await loop.run_in_executor(None, self._fetch_chapter_sync, chuong_id)

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        loop = asyncio.get_running_loop()
        
        # Xoá file cũ nếu tồn tại
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            
        success_count = 0
        failed = []
        
        print(f"Bắt đầu tải từ webnovel.vn: {self.book_id} (Chương {start} đến {end})")
        
        with tqdm(total=total, desc="Scraping WebNovel", unit="chap",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            for i in range(start, end + 1):
                pbar.set_postfix_str(f"ch.{i}")
                
                title, content = await self._fetch_chapter_async(loop, i)
                
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
