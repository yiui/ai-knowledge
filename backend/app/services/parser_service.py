from pathlib import Path
from pypdf import PdfReader
from langchain_community.document_loaders import PyMuPDFLoader


def parse_pdf(file_path: str) -> list[str]:
    """
    返回每页文本
    """
        # 1. 先抽文本
    pages = extract_pdf_text(file_path)

    # 2. 如果文本质量差 → OCR
    if not is_text_valid(pages):
        pages = run_ocr(file_path)

    # 3. 最终兜底过滤
    pages = [p.strip() for p in pages if p and p.strip()]
    print("parse over")
    return pages


def parse_txt(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [f.read()]


def parse_md(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        return [f.read()]




def parse_document(file_path: str):

    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)

    if suffix == ".txt":
        return parse_txt(file_path)

    if suffix == ".md":
        return parse_md(file_path)

    raise ValueError("unsupported file type")



def extract_pdf_text(file_path: str) -> list[str]:
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    pages = []

    for doc in docs:
        text = doc.page_content or ""
        text = text.strip()
        print("text:", text)    
        if text:
            pages.append(text)

    return pages


def is_text_valid(pages: list[str]) -> bool:
    if not pages:
        return False

    total_chars = sum(len(p.strip()) for p in pages)

    # 太少说明是图片PDF
    return total_chars > 50


def run_ocr(file_path: str) -> list[str]:
    """
    这里接 RapidOCR / PaddleOCR
    """
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()

    # 示例：逐页OCR（你可以优化成 image render）
    from pdf2image import convert_from_path

    images = convert_from_path(file_path)

    pages = []

    for img in images:
        result, _ = ocr(img)
        text = "\n".join([r[1] for r in result]) if result else ""
        print("ocr text:", text)
        if text.strip():
            pages.append(text)

    return pages