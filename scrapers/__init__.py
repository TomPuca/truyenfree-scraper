SUPPORTED_SOURCES = ["truyenfree", "tangthuvien", "vietnamthuquan", "webnovel", "ntruyen", "truyenhoangdung"]

def get_scraper(source_name, book_id, **kwargs):
    """
    Factory method khởi tạo scraper tương ứng theo tên nguồn.
    Sử dụng import động để tránh lỗi thiếu thư viện của các scraper khác.
    """
    source_name = source_name.lower()
    if source_name == "truyenfree":
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
    else:
        raise ValueError(
            f"Không tìm thấy scraper cho nguồn '{source_name}'. "
            f"Các nguồn hỗ trợ: {', '.join(SUPPORTED_SOURCES)}"
        )
