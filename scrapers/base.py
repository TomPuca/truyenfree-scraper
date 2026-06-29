from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, book_id, **kwargs):
        self.book_id = book_id
        self.output_file = kwargs.get("output_file", "truyen_output.txt")
        self.book_title = kwargs.get("book_title", book_id)
        self.book_author = kwargs.get("book_author", "Unknown")

    @abstractmethod
    async def scrape(self, start: int, end: int) -> bool:
        """
        Thực hiện cào nội dung truyện từ chương start đến chương end.
        Trả về True nếu cào thành công, False nếu thất bại.
        Dữ liệu cào được ghi vào self.output_file theo định dạng:
        <h1>Tiêu đề chương</h1>
        <h2>Nội dung chương</h2>
        """
        pass
