import asyncio
from playwright.async_api import async_playwright
import os
from tqdm import tqdm
from scrapers.base import BaseScraper

class TruyenFreeScraper(BaseScraper):
    def __init__(self, book_id, **kwargs):
        super().__init__(book_id, **kwargs)
        # Cho phép tuỳ chọn cấu hình proxy qua kwargs, mặc định là proxy ban đầu
        self.proxy = kwargs.get("proxy", {
            "server": "http://1.231.81.166:3128"
        })

    async def _scrape_chapter(self, browser_context, url):
        page = await browser_context.new_page()
        try:
            await page.goto(url, wait_until="load", timeout=120000)
            
            # Extract title
            title = await page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('div, span, a'));
                const chapterEl = elements.find(el => el.innerText.includes('Chương ') && el.innerText.length < 100);
                return chapterEl ? chapterEl.innerText.trim() : "Unknown Chapter";
            }""")
            
            # Extract content using visual sorting and filtering out hidden garbage
            content = await page.evaluate("""() => {
                const container = document.querySelector('article');
                if (!container) return "";
                
                const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
                const textNodes = [];
                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    if (text.length > 0) {
                        const parent = node.parentElement;
                        const style = window.getComputedStyle(parent);
                        const rect = parent.getBoundingClientRect();
                        
                        if (style.display === 'none' || 
                            style.visibility === 'hidden' || 
                            style.opacity === '0' ||
                            rect.width === 0 || 
                            rect.height === 0) {
                            continue;
                        }
                        
                        if (rect.left < -100 || rect.top < -100) continue;
                        
                        if (text.includes('Truyện được đăng bởi Truyen100') || 
                            text.includes('Vui lòng không sao chép')) {
                            continue;
                        }

                        textNodes.push({
                            text: node.textContent,
                            top: rect.top + window.scrollY,
                            left: rect.left + window.scrollX,
                            bottom: rect.bottom + window.scrollY,
                            right: rect.right + window.scrollX,
                            height: rect.height,
                            width: rect.width
                        });
                    }
                }
                
                if (textNodes.length === 0) return "";
                
                textNodes.sort((a, b) => {
                    const threshold = Math.min(a.height, b.height) / 2 || 10;
                    if (Math.abs(a.top - b.top) < threshold) {
                        return a.left - b.left;
                    }
                    return a.top - b.top;
                });
                
                let result = "";
                let lastNode = null;
                for (const node of textNodes) {
                    if (lastNode) {
                        const vGap = node.top - lastNode.top;
                        const hGap = node.left - lastNode.right;
                        const lineH = lastNode.height || 20;
                        
                        if (vGap > lineH * 1.5) {
                            result += "\\n";
                        } else if (vGap > lineH * 0.5) {
                            if (!result.endsWith(' ') && !node.text.startsWith(' ')) {
                                result += " ";
                            }
                        } else if (hGap > 4) {
                            if (!result.endsWith(' ') && !node.text.startsWith(' ')) {
                                result += " ";
                            }
                        }
                    }
                    result += node.text;
                    lastNode = node;
                }
                return result.trim();
            }""")
            
            return title, content
        except Exception as e:
            print(f"Lỗi khi cào {url}: {e}")
            return None, None
        finally:
            await page.close()

    async def scrape(self, start: int, end: int) -> bool:
        total = end - start + 1
        async with async_playwright() as p:
            # Cho phép cấu hình không dùng proxy nếu self.proxy là None
            launch_args = {"headless": True}
            if self.proxy:
                launch_args["proxy"] = self.proxy
                
            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Xoá file cũ nếu tồn tại
            if os.path.exists(self.output_file):
                os.remove(self.output_file)

            success_count = 0
            failed = []

            with tqdm(total=total, desc="Scraping Truyenfree", unit="chap",
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                for i in range(start, end + 1):
                    # Sử dụng book_id động
                    url = f"https://truyenfree.org/truyen/{self.book_id}/chuong-{i}"
                    pbar.set_postfix_str(f"ch.{i}")

                    title, content = await self._scrape_chapter(context, url)

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
                    await asyncio.sleep(1)

            await browser.close()
            print(f"\nHoàn tất cào: {success_count}/{total} chương thành công.")
            if failed:
                print(f"Thất bại ({len(failed)} chương): {failed}")
                
        return success_count > 0
