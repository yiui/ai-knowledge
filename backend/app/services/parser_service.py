import logging
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader
from pypdf import PdfReader

log = logging.getLogger("parser")
log_ocr = logging.getLogger("ocr")


def parse_pdf(file_path: str) -> list[str]:
    """返回每页文本"""

    try:
        # 1. 先抽文本
        pages = extract_pdf_text(file_path)
    except MemoryError:
        log.exception("PDF text extraction OOM, fallback to OCR")
        pages = []
    except Exception:
        log.exception("PDF text extraction failed")
        pages = []

    total_chars = sum(len(p.strip()) for p in pages)
    log.info(
        "text extraction: %d pages, %d total chars, avg %.0f chars/page",
        len(pages), total_chars,
        total_chars / len(pages) if pages else 0,
    )

    # 2. 如果文本质量差 → OCR
    text_valid = is_text_valid(pages)
    log.info("text valid=%s, will%s run OCR", text_valid, " not" if text_valid else "")
    if not text_valid:
        try:
            pages = run_ocr(file_path)
            log.info("OCR produced %d pages", len(pages))
        except MemoryError:
            log.exception("PDF OCR OOM, returning whatever we have")
        except Exception:
            log.exception("PDF OCR failed")

    # 3. 最终兜底过滤
    pages = [p.strip() for p in pages if p and p.strip()]
    log.info("parse over, %d pages after filtering", len(pages))
    for i, page in enumerate(pages):
        log.debug("page %d preview (first 80 chars): %s", i, page[:80])
    return pages


def parse_txt(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [f.read()]


def parse_md(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [f.read()]


def parse_excel(file_path: str) -> list[str]:
    import pandas as pd

    suffix = Path(file_path).suffix.lower()
    engine = "xlrd" if suffix == ".xls" else "openpyxl"

    try:
        sheets = pd.read_excel(file_path, sheet_name=None, engine=engine)
    except Exception as exc:
        raise ValueError(f"无法解析 Excel 文件: {exc}") from exc

    parts: list[str] = []
    headers: list[str] = []
    for sheet_name, df in sheets.items():
        if df is None or df.empty:
            continue
        df = df.fillna("")
        lines: list[str] = []
        prerow:list[str] = []
        for _, row in df.iterrows():
            # 如果当前行和上一行长度相同且headers为空，则认为上一行是标题行
            if len(row.tolist()) == len(prerow) and len(headers) == 0:
                headers=prerow

            cells = [str(v).strip() for v in row if str(v).strip()]
            if cells:
                result = "|".join(
                    f"{k}:{v}"
                    for k, v in zip(headers, cells)
                )
                lines.append(result)
                prerow = cells
        if lines:
            title = str(sheet_name) if sheet_name else "Sheet"
            parts.append(f"【{title}】\n" + "\n".join(lines))

    return parts if parts else [""]


def parse_document(file_path: str):
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)

    if suffix == ".txt":
        return parse_txt(file_path)

    if suffix == ".md":
        return parse_md(file_path)

    if suffix in (".xlsx", ".xls"):
        return parse_excel(file_path)

    raise ValueError(f"unsupported file type: {suffix}")



def extract_pdf_text(file_path: str) -> list[str]:
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    pages = []

    for doc in docs:
        text = doc.page_content or ""
        text = text.strip()
        if text:
            pages.append(text)

    return pages


def is_text_valid(pages: list[str]) -> bool:
    if not pages:
        return False

    total_chars = sum(len(p.strip()) for p in pages)

    # 总字符数太少 → 图片 PDF
    if total_chars <= 50:
        return False

    # 平均每页字符数过低 → 碎片文本（课件类 PDF），强制走 OCR
    avg_chars = total_chars / len(pages)
    if avg_chars < 30:
        return False

    return True


def _get_pdf_page_count(file_path: str) -> int:
    """获取 PDF 总页数，不加载全部内容。"""
    import fitz  # PyMuPDF
    doc = fitz.open(file_path)
    count = doc.page_count
    doc.close()
    return count


def run_ocr(file_path: str) -> list[str]:
    """
    OCR 识别。逐页处理以免 2C4G 小机器内存溢出。
    """
    import gc

    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    from pdf2image import convert_from_path

    # 限制单张图片最大像素（宽×高），防止超大页面撑爆内存
    # 4000×4000 = 16MP，对 OCR 足够了
    Image.MAX_IMAGE_PIXELS = 16_000_000

    total_pages = _get_pdf_page_count(file_path)

    # 内存保护：超过 50 页的 PDF 只 OCR 前 50 页
    MAX_OCR_PAGES = 50
    process_count = min(total_pages, MAX_OCR_PAGES)
    if total_pages > MAX_OCR_PAGES:
        log_ocr.warning(
            "PDF has %d pages, only OCR first %d to conserve memory",
            total_pages, MAX_OCR_PAGES,
        )

    ocr = RapidOCR()
    pages: list[str] = []

    try:
        for page_num in range(1, process_count + 1):
            try:
                # 逐页转换，fmt='jpeg' 比默认 ppm 省内存
                images = convert_from_path(
                    file_path,
                    dpi=120,
                    first_page=page_num,
                    last_page=page_num,
                    fmt='jpeg',
                    grayscale=True,
                )
                if not images:
                    continue

                img = images[0]
                result, _ = ocr(img)

                # 立即释放图片内存
                img.close()
                del images
                del img

                text = "\n".join([r[1] for r in result]) if result else ""
                if text.strip():
                    pages.append(text)

            except MemoryError:
                log_ocr.exception(
                    "OOM at page %d/%d, skip remaining pages", page_num, process_count,
                )
                break
            except Exception:
                log_ocr.exception("OCR page %d/%d failed", page_num, process_count)
    finally:
        del ocr
        gc.collect()

    return pages