import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
from scrapers.base import BaseScraper


class TruyenFullScraper(BaseScraper):
    """
    Scraper cho truyenfull.live
    URL chương: https://truyenfull.live/{book_id}/chuong-{n}/
    """

    BASE_URL = "https://truyenfull.live"

    def __init__(self, book_id, **kwargs):
        super().__init__(book_id, **kwargs)
        self.session_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            "Referer": self.BASE_URL,
        }

    def _build_chapter_url(self, chapter_num: int) -> str:
        return f"{self.BASE_URL}/{self.book_id}/chuong-{chapter_num}/"

    async def _fetch_chapter(self, session: aiohttp.ClientSession, chapter_num: int):
        """Tải và parse một chương. Trả về (title, content) hoặc (None, None) nếu lỗi."""
        url = self._build_chapter_url(chapter_num)
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    print(f"\nChương {chapter_num}: HTTP {resp.status}")
                    return None, None
                html = await resp.text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"\nLỗi tải chương {chapter_num}: {e}")
            return None, None

        soup = BeautifulSoup(html, "html.parser")

        # --- Lấy tiêu đề chương ---
        title_tag = (
            soup.select_one("a.chapter-title")
            or soup.select_one(".chapter-title")
            or soup.select_one("h2.chapter-title")
            or soup.select_one("h1")
        )
        import re as _re
        raw_title = title_tag.get_text(strip=True) if title_tag else f"Chương {chapter_num}"
        # Chuẩn hoá: "Chương1" → "Chương 1", xoá khoảng trắng thừa
        title = _re.sub(r'(Chương)(\d)', r'\1 \2', raw_title).strip()

        # --- Lấy nội dung chương ---
        content_tag = soup.select_one("#chapter-c") or soup.select_one(".chapter-c")
        if not content_tag:
            print(f"\nKhông tìm thấy nội dung chương {chapter_num} tại {url}")
            return None, None

        # Xoá các thẻ quảng cáo / script ẩn
        for junk in content_tag.select("script, style, .ads, [style*='display:none'], [style*='display: none']"):
            junk.decompose()

        # Gộp text theo dòng
        lines = []
        for elem in content_tag.descendants:
            if isinstance(elem, str):
                text = elem.strip()
                if text:
                    lines.append(text)
            elif getattr(elem, "name", None) in ("p", "br", "div"):
                lines.append("")  # xuống dòng

        content = "\n".join(line for line in lines if line or (lines and lines[-1] != ""))
        content = content.strip()

        if not content:
            print(f"\nNội dung chương {chapter_num} rỗng.")
            return None, None

        return title, content

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1

        # Xoá file cũ nếu tồn tại
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

        success_count = 0
        failed = []

        async with aiohttp.ClientSession(headers=self.session_headers) as session:
            with tqdm(
                total=total,
                desc="Scraping TruyenFull",
                unit="chap",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            ) as pbar:
                for chapter_num in range(start, end + 1):
                    pbar.set_postfix_str(f"ch.{chapter_num}")

                    title, content = await self._fetch_chapter(session, chapter_num)

                    if title and content:
                        with open(self.output_file, "a", encoding="utf-8") as f:
                            f.write(f"<h1>{title}</h1>\n")
                            f.write(f"<h2>{content}</h2>\n\n")
                        success_count += 1
                        pbar.set_postfix_str(title[:50])
                    else:
                        failed.append(chapter_num)
                        pbar.set_postfix_str(f"ch.{chapter_num} FAILED")

                    pbar.update(1)
                    # Nghỉ nhỏ để tránh bị chặn
                    await asyncio.sleep(0.5)

        print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
        if failed:
            print(f"Thất bại ({len(failed)} chương): {failed}")

        return success_count > 0
