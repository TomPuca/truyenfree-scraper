import urllib.request
import urllib.error
import re
import os
import time
import asyncio
from html.parser import HTMLParser
from tqdm import tqdm
from scrapers.base import BaseScraper

class TangThuVienParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h1 = False
        self.in_content_div = False
        self.in_p = False
        self.title_parts = []
        self.paragraphs = []
        self.current_paragraph = []
        self.div_nest_level = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "h1" and "text-xl" in attrs_dict.get("class", ""):
            self.in_h1 = True
            
        if tag == "div":
            if self.in_content_div:
                self.div_nest_level += 1
            elif any("source_serif" in c for c in attrs_dict.get("class", "").split()):
                self.in_content_div = True
                self.div_nest_level = 1
                
        if tag == "p" and self.in_content_div:
            self.in_p = True
            self.current_paragraph = []

    def handle_endtag(self, tag):
        if tag == "h1" and self.in_h1:
            self.in_h1 = False
        elif tag == "div" and self.in_content_div:
            self.div_nest_level -= 1
            if self.div_nest_level == 0:
                self.in_content_div = False
        elif tag == "p" and self.in_p:
            self.in_p = False
            text = "".join(self.current_paragraph).strip()
            if text:
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self.in_h1:
            self.title_parts.append(data)
        elif self.in_p:
            self.current_paragraph.append(data)

class TangThuVienScraper(BaseScraper):
    def __init__(self, book_id, **kwargs):
        super().__init__(book_id, **kwargs)
        self.base_url = f"https://tangthuvien.org/{book_id}"

    def _fetch_and_parse(self, url, retries=3):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    if response.status == 200:
                        html_content = response.read().decode('utf-8')
                        parser = TangThuVienParser()
                        parser.feed(html_content)
                        
                        title = "".join(parser.title_parts).strip()
                        title = re.sub(r'\s+', ' ', title)
                        content = "\n".join(parser.paragraphs)
                        
                        if title and content:
                            return title, content
            except Exception as e:
                if attempt == retries - 1:
                    pass
                time.sleep(1)
                
        return None, None

    async def _scrape_chapter_async(self, loop, url):
        return await loop.run_in_executor(None, self._fetch_and_parse, url)

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        loop = asyncio.get_running_loop()
        
        if os.path.exists(self.output_file):
            os.remove(self.output_file)
            
        success_count = 0
        failed = []
        
        print(f"Bắt đầu tải từ tangthuvien.org: {self.book_id} (Chương {start} đến {end})")
        
        with tqdm(total=total, desc="Scraping TT-Vien", unit="chap",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            for i in range(start, end + 1):
                url = f"{self.base_url}/{i}"
                pbar.set_postfix_str(f"ch.{i}")
                
                title, content = await self._scrape_chapter_async(loop, url)
                
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
                await asyncio.sleep(0.5)
                
        print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
        if failed:
            print(f"Thất bại ({len(failed)} chương): {failed}")
            
        return success_count > 0
