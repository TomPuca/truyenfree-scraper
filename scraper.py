import asyncio
from playwright.async_api import async_playwright
import sys
import os
from tqdm import tqdm

async def scrape_chapter(browser_context, url):
    page = await browser_context.new_page()
    try:
        await page.goto(url, wait_until="load", timeout=120000)
        
        # Based on typical Next.js apps, let's look for a div that contains the text
        # If we can't find a class, we can target by text content
        
        # Extract title - let's try a better way
        title = await page.evaluate("""() => {
            const elements = Array.from(document.querySelectorAll('div, span, a'));
            const chapterEl = elements.find(el => el.innerText.includes('Chương ') && el.innerText.length < 100);
            return chapterEl ? chapterEl.innerText.trim() : "Unknown Chapter";
        }""")
         # Extract content using visual sorting and filtering out hidden garbage
        content = await page.evaluate("""() => {
            // Find the main container - the article with the story text
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
                    
                    // Filter out hidden elements (common anti-scraping technique)
                    if (style.display === 'none' || 
                        style.visibility === 'hidden' || 
                        style.opacity === '0' ||
                        rect.width === 0 || 
                        rect.height === 0) {
                        continue;
                    }
                    
                    // Filter out elements that are likely injected junk
                    // These often have absolute positioning or are off-screen
                    if (rect.left < -100 || rect.top < -100) continue;
                    
                    // Filter out known watermark text
                    if (text.includes('Truyện được đăng bởi Truyen100') || 
                        text.includes('Vui lòng không sao chép')) {
                        continue;
                    }

                    textNodes.push({
                        text: node.textContent, // Keep original text (with spaces if any)
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
            
            // Sort by top, then left
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
                        // True paragraph break
                        result += "\\n";
                    } else if (vGap > lineH * 0.5) {
                        // Line wrap within same paragraph — join with a space
                        if (!result.endsWith(' ') && !node.text.startsWith(' ')) {
                            result += " ";
                        }
                    } else if (hGap > 4) {
                        // Same line, gap between words/segments
                        if (!result.endsWith(' ') && !node.text.startsWith(' ')) {
                            result += " ";
                        }
                    }
                    // else: adjacent scrambled chars — no separator
                }
                result += node.text;
                lastNode = node;
            }
            return result.trim();
        }""")
        
        return title, content
    except Exception as e:
        print(f"General error scraping {url}: {e}")
        return None, None
    finally:
        await page.close()

async def main(start, end):
    proxy = {
        "server": "http://1.231.81.166:3128"
    }

    total = end - start + 1
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=proxy)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        output_file = "truyen_output.txt"
        if os.path.exists(output_file):
            os.remove(output_file)

        success_count = 0
        failed = []

        with tqdm(total=total, desc="Scraping", unit="chap",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            for i in range(start, end + 1):
                url = f"https://truyenfree.org/truyen/dich-quang-am-chi-ngoai/chuong-{i}"
                pbar.set_postfix_str(f"ch.{i}")

                title, content = await scrape_chapter(context, url)

                if title and content:
                    with open(output_file, "a", encoding="utf-8") as f:
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
        print(f"\nHoàn tất: {success_count}/{total} chapter. File: {output_file}")
        if failed:
            print(f"Thất bại ({len(failed)} chapter): {failed}")

if __name__ == "__main__":
    # Fix for Windows console encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    if len(sys.argv) < 3:
        print("Usage: python scraper.py <start_chapter> <end_chapter>")
    else:
        try:
            start_ch = int(sys.argv[1])
            end_ch = int(sys.argv[2])
            asyncio.run(main(start_ch, end_ch))
        except ValueError:
            print("Error: Start and end chapters must be integers.")
