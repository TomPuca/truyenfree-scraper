import re

SUPPORTED_SOURCES = ["truyenfull", "truyenfree", "tangthuvien", "vietnamthuquan", "webnovel", "ntruyen", "truyenhoangdung", "tvtruyen"]

def detect_source_and_book_id(input_str: str) -> tuple[str, str]:
    """
    Tự động nhận biết nguồn cào (source) và trích xuất book_id từ URL hoặc chuỗi nhập vào.
    Trả về (source_name, book_id).
    """
    if not input_str:
        return None, None

    input_str = input_str.strip()

    # 0. truyenfull.live
    if "truyenfull.live" in input_str or "truyenfull" in input_str:
        match = re.search(r'truyenfull\.live/([^/?#]+)', input_str)
        if match:
            return "truyenfull", match.group(1).strip("/")
        return "truyenfull", input_str

    # 1. tvtruyen.cc
    if "tvtruyen.cc" in input_str or "truyentv" in input_str:
        match = re.search(r'tvtruyen\.cc/([^/]+?)(?:\.html)?$', input_str)
        if match:
            return "tvtruyen", match.group(1)
        match = re.search(r'tvtruyen\.cc/([^/]+)', input_str)
        if match:
            return "tvtruyen", match.group(1).replace('.html', '')
        return "tvtruyen", input_str

    # 2. truyenhoangdung.xyz
    if "truyenhoangdung" in input_str:
        match = re.search(r'truyenhoangdung\.xyz/([^/]+)', input_str)
        if match:
            return "truyenhoangdung", match.group(1)
        return "truyenhoangdung", input_str

    # 3. ntruyen.xyz
    if "ntruyen" in input_str:
        match = re.search(r'ntruyen\.xyz/(?:truyen|doc-truyen)/([^/?#]+)', input_str)
        if match:
            slug = match.group(1)
            slug_match = re.search(r'^(.*?)-chuong-\d+', slug)
            if slug_match:
                slug = slug_match.group(1)
            return "ntruyen", slug
        return "ntruyen", input_str

    # 4. tangthuvien.vn / tangthuvien.org
    if "tangthuvien" in input_str:
        match = re.search(r'tangthuvien\.(?:vn|org)/(?:doc-truyen/)?([^/?#]+)', input_str)
        if match:
            return "tangthuvien", match.group(1)
        return "tangthuvien", input_str

    # 5. vietnamthuquan
    if "vietnamthuquan" in input_str:
        match = re.search(r'tid=([^&]+)', input_str)
        if match:
            return "vietnamthuquan", match.group(1)
        return "vietnamthuquan", input_str

    # 6. webnovel
    if "webnovel" in input_str:
        match = re.search(r'webnovel\.com/(?:book/)?([^/?#]+)', input_str)
        if match:
            return "webnovel", match.group(1)
        return "webnovel", input_str

    # 7. truyenfree
    if "truyenfree" in input_str:
        match = re.search(r'truyenfree\.(?:org|net)/(?:truyen/)?([^/?#]+)', input_str)
        if match:
            return "truyenfree", match.group(1)
        return "truyenfree", input_str

    return None, input_str


def get_scraper(source_name, book_id=None, **kwargs):
    """
    Factory method khởi tạo scraper tương ứng theo tên nguồn.
    Tự động nhận biết nếu source_name hoặc book_id chứa URL.
    """
    # Nếu source_name chứa URL, tự động nhận biết source và book_id
    if source_name and ("http://" in source_name or "https://" in source_name or "." in source_name):
        detected_src, detected_bid = detect_source_and_book_id(source_name)
        if detected_src:
            source_name = detected_src
            if detected_bid and not book_id:
                book_id = detected_bid

    # Nếu book_id chứa URL, tự động làm sạch book_id và nhận biết source
    if book_id and ("http://" in book_id or "https://" in book_id or "." in book_id):
        detected_src, detected_bid = detect_source_and_book_id(book_id)
        if detected_src and (not source_name or source_name not in SUPPORTED_SOURCES):
            source_name = detected_src
        if detected_bid:
            book_id = detected_bid

    source_name = source_name.lower() if source_name else "tvtruyen"

    if source_name == "truyenfull":
        from .truyenfull import TruyenFullScraper
        return TruyenFullScraper(book_id, **kwargs)
    elif source_name == "truyenfree":
        from .truyenfree import TruyenFreeScraper
        return TruyenFreeScraper(book_id, **kwargs)
    elif source_name == "tangthuvien":
        from .tangthuvien import TangThuVienScraper
        return TangThuVienScraper(book_id, **kwargs)
    elif source_name == "vietnamthuquan":
        from .vietnamthuquan import VietnamThuQuanScraper
        return VietnamThuQuanScraper(book_id, **kwargs)
    elif source_name == "webnovel":
        from .webnovel import WebNovelScraper
        return WebNovelScraper(book_id, **kwargs)
    elif source_name == "ntruyen":
        from .ntruyen import NTruyenScraper
        return NTruyenScraper(book_id, **kwargs)
    elif source_name == "truyenhoangdung":
        from .truyenhoangdung import TruyenHoangDungScraper
        return TruyenHoangDungScraper(book_id, **kwargs)
    elif source_name == "tvtruyen":
        from .tvtruyen import TVTruyenScraper
        return TVTruyenScraper(book_id, **kwargs)
    else:
        raise ValueError(
            f"Không tìm thấy scraper cho nguồn '{source_name}'. "
            f"Các nguồn hỗ trợ: {', '.join(SUPPORTED_SOURCES)}"
        )

