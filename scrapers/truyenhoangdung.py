import asyncio
import urllib.request
import urllib.error
import re
import os
import html as html_lib
import time
from tqdm import tqdm
from scrapers.base import BaseScraper


class TruyenHoangDungScraper(BaseScraper):
    """
    Scraper cho website truyenhoangdung.xyz.

    Định dạng URL chương:
        https://www.truyenhoangdung.xyz/{book_id}/chuong-{chapter_number}/

    Ví dụ book_id: 'ai-bao-han-tu-tien-dich'

    Trang web trả về HTML đầy đủ server-side, do đó không cần trình duyệt
    headless (Playwright). Sử dụng urllib.request để tải nhanh hơn nhiều.
    """

    BASE_URL = "https://www.truyenhoangdung.xyz"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self, book_id, **kwargs):
        super().__init__(book_id, **kwargs)

    # ------------------------------------------------------------------
    # Phương thức nội bộ: tải + phân tích đồng bộ
    # ------------------------------------------------------------------

    def _fetch_and_parse(self, chapter_num: int, retries: int = 3):
        """
        Tải trang chương và trích xuất tiêu đề + nội dung.

        Trả về (title, content) hoặc (None, None) nếu thất bại.
        """
        url = f"{self.BASE_URL}/{self.book_id}/chuong-{chapter_num}/"

        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=self.HEADERS)
                with urllib.request.urlopen(req, timeout=20) as response:
                    raw_bytes = response.read()
                    try:
                        raw_html = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        raw_html = raw_bytes.decode("utf-8", errors="replace")

                    title = self._parse_title(raw_html, chapter_num)
                    content = self._parse_content(raw_html)

                    if title and content:
                        return title, content

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Chương không tồn tại, không thử lại
                    return None, None
                if attempt == retries - 1:
                    print(f"\n  [Lỗi HTTP {e.code}] Chương {chapter_num}: {url}")
                time.sleep(1.5)

            except Exception as e:
                if attempt == retries - 1:
                    print(f"\n  [Lỗi] Chương {chapter_num}: {e}")
                time.sleep(1.5)

        return None, None

    # ------------------------------------------------------------------
    # Phân tích tiêu đề
    # ------------------------------------------------------------------

    def _parse_title(self, html: str, chapter_num: int) -> str:
        """
        Trích xuất tiêu đề chương.

        Ưu tiên thẻ <option selected> trong dropdown chọn chương.
        Fallback về <li class="active"> trong breadcrumb.
        """
        # Ưu tiên 1: <option ... selected>Chương 70: Ma Giáo (2)</option>
        match = re.search(
            r'<option[^>]+selected[^>]*>\s*(.*?)\s*</option>', html
        )
        if match:
            return html_lib.unescape(match.group(1).strip())

        # Ưu tiên 2: breadcrumb active
        match = re.search(r'<li\s+class=["\']active["\']>\s*(.*?)\s*</li>', html)
        if match:
            return html_lib.unescape(match.group(1).strip())

        return f"Chương {chapter_num}"

    # ------------------------------------------------------------------
    # Phân tích nội dung
    # ------------------------------------------------------------------

    def _parse_content(self, html: str) -> str:
        """
        Trích xuất và làm sạch nội dung chương từ div#noidung.
        """
        # Lấy toàn bộ nội dung trong thẻ <div id="noidung">
        match = re.search(
            r'<div[^>]*\bid=["\']noidung["\'][^>]*>(.*?)</div>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return ""

        raw = match.group(1)

        # Chuyển <p> và <br> thành xuống dòng để tách đoạn văn
        raw = re.sub(r'</?p[^>]*>', '\n', raw, flags=re.IGNORECASE)
        raw = re.sub(r'<br\s*/?>', '\n', raw, flags=re.IGNORECASE)

        # Xóa tất cả thẻ HTML còn lại
        raw = re.sub(r'<[^>]+>', '', raw)

        # Giải mã HTML entities (vd: m&agrave; -> mà)
        raw = html_lib.unescape(raw)

        # Làm sạch khoảng trắng, loại bỏ dòng trống
        paragraphs = []
        for line in raw.split('\n'):
            line = line.strip()
            if line:
                paragraphs.append(line)

        return '\n'.join(paragraphs)

    # ------------------------------------------------------------------
    # Phương thức async wrapper để chạy trong event loop
    # ------------------------------------------------------------------

    async def _fetch_chapter_async(self, loop, chapter_num: int):
        return await loop.run_in_executor(
            None, self._fetch_and_parse, chapter_num
        )

    # ------------------------------------------------------------------
    # Phương thức scrape chính (interface BaseScraper)
    # ------------------------------------------------------------------

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        loop = asyncio.get_running_loop()

        # Xóa file output cũ nếu tồn tại
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

        success_count = 0
        failed = []

        print(
            f"Bắt đầu tải từ truyenhoangdung.xyz: {self.book_id} "
            f"(Chương {start} đến {end})"
        )

        with tqdm(
            total=total,
            desc="Scraping TruyenHD",
            unit="chap",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        ) as pbar:
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
                # Delay nhẹ để tránh overload server
                await asyncio.sleep(0.3)

        print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
        if failed:
            print(f"Thất bại ({len(failed)} chương): {failed}")

        return success_count > 0
