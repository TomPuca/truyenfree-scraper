"""
make_epub.py - Chuyển đổi truyen_output.txt sang file EPUB

Cú pháp:
    python make_epub.py [input_file] [output_file] [book_title] [author]

Mặc định:
    python make_epub.py truyen_output.txt output.epub "Quang Âm Chi Ngoại" "Nhĩ Căn"
"""

import sys
import re
import os
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from ebooklib import epub
from tqdm import tqdm

# ── Cấu hình mặc định ──────────────────────────────────────────────────────────
DEFAULT_INPUT  = "truyen_output.txt"
DEFAULT_OUTPUT = "output.epub"
DEFAULT_TITLE  = "[Dịch] Quang Âm Chi Ngoại"
DEFAULT_AUTHOR = "Nhĩ Căn"
DEFAULT_LANG   = "vi"
# ───────────────────────────────────────────────────────────────────────────────

CSS = """\
@charset "UTF-8";

body {
    font-family: "Noto Serif", "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.8;
    margin: 2em 1.5em;
    color: #1a1a1a;
    text-align: left;
}
h1 {
    font-size: 1.2em;
    font-weight: bold;
    margin: 2em 0 1em 0;
    text-align: center;
}
p {
    margin: 0.5em 0;
    text-indent: 2em;
}
"""


def parse_input(filepath):
    """Đọc file và tách thành danh sách (title, content)."""
    import unicodedata
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    # Normalize về NFC: gộp ký tự + dấu thành 1 code point (tránh dấu bị tách)
    raw = unicodedata.normalize('NFC', raw)

    chapters = []
    # Tìm tất cả cặp <h1>...</h1> và <h2>...</h2>
    pattern = re.compile(
        r'<h1>(.*?)</h1>\s*<h2>(.*?)</h2>',
        re.DOTALL
    )
    for m in pattern.finditer(raw):
        title   = m.group(1).strip()
        content = m.group(2).strip()
        chapters.append((title, content))

    return chapters


def content_to_html(title, content):
    """Chuyển nội dung text thành HTML cho một chapter."""
    # Mỗi dòng (đoạn văn) → <p>
    lines = content.split('\n')
    paragraphs = []
    for line in lines:
        line = line.strip()
        if line:
            # Escape HTML entities
            line = (line
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;'))
            paragraphs.append(f'<p>{line}</p>')

    body = '\n'.join(paragraphs)
    safe_title = (title
                  .replace('&', '&amp;')
                  .replace('<', '&lt;')
                  .replace('>', '&gt;'))

    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="vi" lang="vi">
<head>
  <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8"/>
  <meta charset="utf-8"/>
  <title>{safe_title}</title>
  <link rel="stylesheet" type="text/css" href="../Styles/style.css"/>
</head>
<body>
  <h1>{safe_title}</h1>
  {body}
</body>
</html>"""


def make_epub(input_file, output_file, book_title, author):
    print(f"Đang đọc: {input_file}")
    chapters = parse_input(input_file)

    if not chapters:
        print("Không tìm thấy chapter nào trong file.")
        return

    print(f"Tìm thấy {len(chapters)} chapter. Đang tạo EPUB...")

    book = epub.EpubBook()
    book.set_identifier("truyenfree-001")
    book.set_title(book_title)
    book.set_language(DEFAULT_LANG)
    book.add_author(author)

    # Cover image
    cover_file = "Bia.webp"
    if os.path.exists(cover_file):
        with open(cover_file, "rb") as f:
            cover_data = f.read()
        book.set_cover("cover.webp", cover_data)
        print(f"Đã thêm ảnh bìa: {cover_file}")
    else:
        print(f"Không tìm thấy ảnh bìa ({cover_file}), bỏ qua.")

    # CSS
    style = epub.EpubItem(
        uid="style",
        file_name="Styles/style.css",
        media_type="text/css",
        content=CSS.encode("utf-8")
    )
    book.add_item(style)

    epub_chapters = []
    with tqdm(total=len(chapters), desc="Building EPUB", unit="chap") as pbar:
        for idx, (title, content) in enumerate(chapters, 1):
            filename = f"chapter_{idx:04d}.xhtml"
            ch = epub.EpubHtml(
                title=title,
                file_name=filename,
                lang=DEFAULT_LANG
            )
            html_str = content_to_html(title, content)
            ch.content = html_str.encode("utf-8")
            ch.add_item(style)
            book.add_item(ch)
            epub_chapters.append(ch)
            pbar.set_postfix_str(title[:40])
            pbar.update(1)

    # Mục lục và spine
    book.toc = tuple(epub_chapters)
    book.spine = ["nav"] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_file, book, {})
    size_kb = os.path.getsize(output_file) // 1024
    print(f"\nHoàn tất! File EPUB: {output_file} ({size_kb} KB)")
    print(f"Tổng số chapter: {len(chapters)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    input_file  = args[0] if len(args) > 0 else DEFAULT_INPUT
    output_file = args[1] if len(args) > 1 else DEFAULT_OUTPUT
    book_title  = args[2] if len(args) > 2 else DEFAULT_TITLE
    author      = args[3] if len(args) > 3 else DEFAULT_AUTHOR

    if not os.path.exists(input_file):
        print(f"Không tìm thấy file: {input_file}")
        sys.exit(1)

    make_epub(input_file, output_file, book_title, author)
