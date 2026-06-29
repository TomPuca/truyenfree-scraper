import asyncio
import os
import re
import time
import json
import urllib.request
from tqdm import tqdm
from playwright.async_api import async_playwright
from scrapers.base import BaseScraper

class NTruyenScraper(BaseScraper):
    def __init__(self, book_id, **kwargs):
        # book_id ở đây chính là book slug (ví dụ: 'ai-bao-han-tu-tien')
        super().__init__(book_id, **kwargs)
        self.base_url = "https://ntruyen.xyz"
        self.api_base_url = "https://api.ntruyen.xyz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": self.base_url,
            "Referer": self.base_url + "/"
        }

    async def _get_novel_id_and_slug(self, page) -> tuple[int, str]:
        """Truy cập trang chủ truyện để lấy novel ID và book slug chính xác"""
        url = f"{self.base_url}/truyen/{self.book_id}"
        print(f"Đang phân tích trang chủ truyện tại {url} để tìm ID...")
        
        # Chặn các tài nguyên không cần thiết để load nhanh
        await page.route("**/*.{png,jpg,jpeg,webp,gif,css,woff,woff2,svg}", lambda route: route.abort())
        
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if response.status != 200:
            raise ValueError(f"Không thể truy cập trang chủ truyện, status: {response.status}")
            
        html = await page.content()
        
        # Tìm novel ID từ props của Next.js
        # Ví dụ: "id":41998,...,"slug":"ai-bao-han-tu-tien"
        # Hoặc tìm "id":(\d+) bất kỳ gần với slug
        match = re.search(r'"id":(\d+),[^}]*?"slug":"' + re.escape(self.book_id) + r'"', html)
        if not match:
            # Tìm rộng hơn
            match = re.search(r'"id":(\d+),.*?"slug":"' + re.escape(self.book_id) + r'"', html)
            
        if match:
            novel_id = int(match.group(1))
            return novel_id, self.book_id
        
        # Thử tìm ID mặc định nếu là bộ truyện Ai Bảo Hắn Tu Tiên!
        if self.book_id == "ai-bao-han-tu-tien":
            return 41998, self.book_id
            
        raise ValueError("Không tìm thấy Novel ID từ trang chủ truyện.")

    def _fetch_api_page_sync(self, novel_id, page_num):
        """Gửi request đồng bộ đến API của ntruyen để lấy danh sách chương"""
        url = f"{self.api_base_url}/novels/{novel_id}/chapters?page={page_num}&sort=asc"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"\nLỗi khi gọi API trang danh sách chương {page_num}: {e}")
            return None

    async def _fetch_api_page_async(self, loop, novel_id, page_num):
        return await loop.run_in_executor(None, self._fetch_api_page_sync, novel_id, page_num)

    async def _build_chapter_map(self, novel_id):
        """Lấy toàn bộ danh sách chương từ API để lập bản đồ mapping chương -> ID/slug"""
        print("Đang tải danh sách chương từ API...")
        loop = asyncio.get_running_loop()
        
        # Lấy trang 1 trước để biết tổng số trang
        first_page = await self._fetch_api_page_async(loop, novel_id, 1)
        if not first_page or "chapters" not in first_page:
            raise ValueError("Không thể tải danh sách chương từ trang 1.")
            
        total_pages = first_page.get("totalPages", 1)
        all_chapters = list(first_page["chapters"])
        
        # Fetch các trang còn lại song song
        if total_pages > 1:
            tasks = [self._fetch_api_page_async(loop, novel_id, p) for p in range(2, total_pages + 1)]
            results = await asyncio.gather(*tasks)
            for res in results:
                if res and "chapters" in res:
                    all_chapters.extend(res["chapters"])
                    
        # Xây dựng map
        chapter_map = {}
        for idx, chap in enumerate(all_chapters, 1):
            chap_id = chap.get("id")
            chap_slug = chap.get("slug")
            
            # Cố gắng trích xuất số chương từ slug (ví dụ: chuong-1 -> 1)
            # Hoặc tên (Chương 1367: Phiên ngoại (3) -> 1367)
            chap_num = None
            slug_match = re.search(r'chuong-(\d+)', chap_slug)
            if slug_match:
                chap_num = int(slug_match.group(1))
            else:
                name_match = re.search(r'Chương\s+(\d+)', chap.get("name", ""))
                if name_match:
                    chap_num = int(name_match.group(1))
                    
            # Fallback nếu không parse được số chương thì dùng index
            if chap_num is None:
                chap_num = idx
                
            chapter_map[chap_num] = {
                "id": chap_id,
                "slug": chap_slug
            }
            
        print(f"Đã lập bản đồ thành công {len(chapter_map)} chương truyện.")
        return chapter_map

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        
        async with async_playwright() as p:
            # Khởi tạo browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # 1. Tìm novel ID và slug
                novel_id, book_slug = await self._get_novel_id_and_slug(page)
                
                # 2. Xây dựng bản đồ chương
                chapter_map = await self._build_chapter_map(novel_id)
            except Exception as e:
                print(f"Lỗi khởi chạy scraper: {e}")
                await browser.close()
                return False
                
            # Xoá file cũ nếu tồn tại
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
                
            success_count = 0
            failed = []
            
            print(f"Bắt đầu tải từ ntruyen.xyz: {self.book_id} (Chương {start} đến {end})")
            
            # Setup routing để block tài nguyên
            await page.route("**/*.{png,jpg,jpeg,webp,gif,css,woff,woff2,svg}", lambda route: route.abort())
            
            with tqdm(total=total, desc="Scraping nTruyen", unit="chap",
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                for i in range(start, end + 1):
                    pbar.set_postfix_str(f"ch.{i}")
                    
                    if i not in chapter_map:
                        failed.append(i)
                        pbar.set_postfix_str(f"ch.{i} NOT FOUND")
                        pbar.update(1)
                        continue
                        
                    chap_info = chapter_map[i]
                    chap_slug = chap_info["slug"]
                    chap_id = chap_info["id"]
                    
                    url = f"{self.base_url}/doc-truyen/{book_slug}-{chap_slug}-{chap_id}"
                    
                    # Cào nội dung
                    title, content = None, None
                    for attempt in range(3):
                        try:
                            # Tải trang với domcontentloaded để tối ưu tốc độ
                            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                            
                            # Trích xuất và làm sạch bằng JS trong trình duyệt
                            title, raw_html_content = await page.evaluate("""() => {
                                const titleEl = document.querySelector('h1');
                                const titleText = titleEl ? titleEl.innerHTML.replace(/<!--.*?-->/g, '').trim() : '';
                                
                                const contentEl = document.querySelector('div.prose');
                                if (!contentEl) return [titleText, ''];
                                
                                const clone = contentEl.cloneNode(true);
                                clone.querySelectorAll('br').forEach(br => br.replaceWith('\\n'));
                                return [titleText, clone.textContent];
                            }""")
                            
                            if title and raw_html_content:
                                # Làm sạch khoảng trắng và các dòng trống
                                lines = []
                                for line in raw_html_content.split('\n'):
                                    line = line.strip()
                                    if line:
                                        lines.append(line)
                                        
                                content = "\n".join(lines)
                                break
                        except Exception:
                            await asyncio.sleep(1)
                            
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
                    await asyncio.sleep(0.4)
                    
            await browser.close()
            
            print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
            if failed:
                print(f"Thất bại ({len(failed)} chương): {failed}")
                
            return success_count > 0
