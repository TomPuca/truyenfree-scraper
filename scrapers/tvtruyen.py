import asyncio
import os
import re
from tqdm import tqdm
from playwright.async_api import async_playwright
from scrapers.base import BaseScraper

class TVTruyenScraper(BaseScraper):
    """
    Scraper cho website tvtruyen.cc (TruyenTV).

    Định dạng URL trang chủ:
        https://www.tvtruyen.cc/{book_id}.html
    Ví dụ book_id: 'he-thong-manh-nhat-dich' hoặc 'he-thong-manh-nhat-dich.html'
    hoặc URL đầy đủ 'https://www.tvtruyen.cc/he-thong-manh-nhat-dich.html'

    Yêu cầu sử dụng Playwright + Proxy do tvtruyen.cc có thể chặn request trực tiếp.
    """

    BASE_URL = "https://www.tvtruyen.cc"

    def __init__(self, book_id, **kwargs):
        # Tự động trích xuất slug từ URL hoặc chuỗi book_id
        if "tvtruyen.cc/" in book_id:
            match = re.search(r'tvtruyen\.cc/([^/]+?)(?:\.html)?$', book_id)
            if match:
                book_id = match.group(1)
        if book_id.endswith(".html"):
            book_id = book_id[:-5]

        super().__init__(book_id, **kwargs)

        # Cấu hình proxy qua kwargs, mặc định là proxy mặc định của dự án
        self.proxy = kwargs.get("proxy", {
            "server": "http://1.231.81.166:3128"
        })

    async def _fetch_chapter_map_page(self, page, page_num: int) -> dict:
        """Lấy danh sách link chương từ trang danh sách chương của truyện."""
        url = f"{self.BASE_URL}/{self.book_id}.html?page={page_num}"
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            chapter_links = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('#list-chapter a[href*="/chuong-"], a[href*="/chuong-"]'));
                return anchors.map(a => ({
                    href: a.href,
                    text: a.innerText.trim()
                }));
            }""")

            chapter_map = {}
            for item in chapter_links:
                match = re.search(r'/chuong-(\d+)', item["href"])
                if match:
                    chap_num = int(match.group(1))
                    chapter_map[chap_num] = item["href"]
            return chapter_map
        except Exception as e:
            print(f"\n  [Lỗi] Không thể tải trang danh sách chương page={page_num}: {e}")
            return {}

    async def _get_start_url(self, page, target_chapter: int) -> tuple[str, dict]:
        """Tải các trang danh sách để tìm URL bắt đầu cho target_chapter."""
        chapter_map = {}
        page_num = 1
        max_pages = 30

        while page_num <= max_pages:
            current_map = await self._fetch_chapter_map_page(page, page_num)
            if not current_map:
                break

            chapter_map.update(current_map)
            if target_chapter in chapter_map:
                return chapter_map[target_chapter], chapter_map

            # Kiểm tra xem có trang tiếp theo không
            has_next = await page.evaluate(f"() => !!document.querySelector('a[href*=\"page={page_num + 1}\"]')")
            if not has_next:
                break

            page_num += 1

        if target_chapter in chapter_map:
            return chapter_map[target_chapter], chapter_map

        return None, chapter_map

    async def _scrape_chapter_content(self, page, url: str) -> tuple[str, str, str]:
        """Cào tiêu đề, nội dung và link chương tiếp theo từ URL chương."""
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            title, content, next_url = await page.evaluate("""() => {
                // Trích xuất tiêu đề
                let titleStr = "";
                const h1 = document.querySelector('h1');
                if (h1) {
                    const text = h1.innerText.trim();
                    if (text.includes(' / ')) {
                        titleStr = text.split(' / ').pop().trim();
                    } else {
                        titleStr = text;
                    }
                }
                if (!titleStr) {
                    const h2 = document.querySelector('h2');
                    titleStr = h2 ? h2.innerText.replace(/^#\\d+\\.\\s*/, '').trim() : '';
                }

                // Trích xuất nội dung
                let contentStr = "";
                const contentEl = document.querySelector('#chapter-content');
                if (contentEl) {
                    const clone = contentEl.cloneNode(true);
                    // Xóa các phần tử không cần thiết
                    clone.querySelectorAll('.ads, .advertisement, script, style, .report').forEach(el => el.remove());
                    clone.querySelectorAll('br').forEach(br => br.replaceWith('\\n'));
                    clone.querySelectorAll('p').forEach(p => p.prepend(document.createTextNode('\\n')));

                    const lines = clone.innerText.split('\\n')
                        .map(l => l.trim())
                        .filter(l => l.length > 0);
                    contentStr = lines.join('\\n');
                }

                // Trích xuất link chương tiếp theo
                const anchors = Array.from(document.querySelectorAll('a'));
                const nextBtn = anchors.find(a => a.innerText.includes('Chương tiếp') || a.innerText.includes('Chương sau'));
                const nextHref = nextBtn ? nextBtn.href : null;

                return [titleStr, contentStr, nextHref];
            }""")

            content = self._clean_content(content)
            return title, content, next_url
        except Exception as e:
            print(f"\n  [Lỗi] Không thể cào chương tại {url}: {e}")
            return None, None, None

    def _clean_content(self, text: str) -> str:
        """Lọc bỏ các câu quảng cáo, thủy ấn và footer của TruyenTV."""
        if not text:
            return ""
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            l_str = line.strip()
            if not l_str:
                continue
            # Lọc bỏ các dòng chứa watermark/quảng cáo của TruyenTV & tvtruyen.cc
            l_lower = l_str.lower()
            if "truyentv" in l_lower or "tvtruyen.cc" in l_lower:
                continue
            if re.search(r'-+\s*oo0oo\s*-+', l_str, re.IGNORECASE) or l_str == "oo0oo":
                continue
            if "bạn vừa hoàn thành chương" in l_lower:
                continue
            if "truyện được đăng" in l_lower:
                continue
            if "website truyện chữ" in l_lower:
                continue
            cleaned_lines.append(l_str)
        return "\n".join(cleaned_lines)

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1

        async with async_playwright() as p:
            launch_args = {"headless": True}
            if self.proxy:
                launch_args["proxy"] = self.proxy

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Chặn tải các tài nguyên hình ảnh/media/font để tăng tốc độ cào
            await page.route(
                "**/*.{png,jpg,jpeg,webp,gif,css,woff,woff2,svg,mp4}",
                lambda route: route.abort()
            )

            print(f"Đang chuẩn bị cào tvtruyen.cc cho truyện '{self.book_id}' (Chương {start} -> {end})...")

            # Tìm URL bắt đầu cho chương start
            current_url, chapter_map = await self._get_start_url(page, start)
            if not current_url:
                print(f"Không tìm thấy URL cho chương bắt đầu {start}.")
                await browser.close()
                return False

            # Xóa file output cũ nếu tồn tại
            if os.path.exists(self.output_file):
                os.remove(self.output_file)

            success_count = 0
            failed = []

            with tqdm(
                total=total,
                desc="Scraping TVTruyen",
                unit="chap",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            ) as pbar:
                for i in range(start, end + 1):
                    pbar.set_postfix_str(f"ch.{i}")

                    if not current_url:
                        # Fallback nếu không có next_url: tìm trong chapter_map
                        if i in chapter_map:
                            current_url = chapter_map[i]
                        else:
                            # Tải thêm map nếu chưa có
                            current_url, chapter_map = await self._get_start_url(page, i)

                    if not current_url:
                        failed.append(i)
                        pbar.set_postfix_str(f"ch.{i} MISSING URL")
                        pbar.update(1)
                        continue

                    title, content, next_url = await self._scrape_chapter_content(page, current_url)

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
                    current_url = next_url
                    await asyncio.sleep(0.3)

            await browser.close()

            print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
            if failed:
                print(f"Thất bại ({len(failed)} chương): {failed}")

            return success_count > 0
