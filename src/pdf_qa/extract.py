"""Page-preserving PDF extraction, local OCR, and character-based chunking."""

import math
import re
from contextlib import ExitStack, closing
from io import BytesIO

import pypdfium2 as pdfium
import pytesseract
from pypdf import PdfReader

from pdf_qa.types import AppError, Chunk, Page, Settings

MAX_BYTES = 50 * 1024 * 1024
MAX_PAGES = 200
MAX_OCR_PIXELS = 40_000_000
OCR_SCALE = 300 / 72
OCR_TIMEOUT = 30


def _ocr_page(document, index: int) -> str:
    with closing(document[index]) as page:
        width, height = page.get_size()
        if not all(math.isfinite(value) and value > 0 for value in (width, height)):
            raise AppError(f"Page {index + 1} has invalid dimensions.")
        pixels = math.ceil(width * OCR_SCALE) * math.ceil(height * OCR_SCALE)
        if pixels > MAX_OCR_PIXELS:
            raise AppError(
                f"Page {index + 1} exceeds the 40-million-pixel OCR limit at 300 DPI. "
                "Resize that page before uploading."
            )
        with closing(page.render(scale=OCR_SCALE)) as bitmap, closing(bitmap.to_pil()) as image:
            return pytesseract.image_to_string(image, lang="eng", timeout=OCR_TIMEOUT)


def extract_pages(
    pdf_bytes: bytes, ocr_mode: str = "auto", progress=None
) -> tuple[list[Page], list[str]]:
    """Extract every physical page, using local English OCR when required."""
    if ocr_mode not in ("auto", "force"):
        raise AppError("Extraction mode must be auto or force.")
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes:
        raise AppError("Upload a nonempty PDF file.")
    if len(pdf_bytes) > MAX_BYTES:
        raise AppError("The PDF exceeds the 50 MiB upload limit.")
    if b"%PDF-" not in pdf_bytes[:1024]:
        raise AppError("This file is not a PDF. Upload a valid PDF file.")

    pages, warnings = [], []
    try:
        with ExitStack() as resources:
            stream = resources.enter_context(BytesIO(pdf_bytes))
            reader = resources.enter_context(PdfReader(stream, strict=True))
            if reader.is_encrypted:
                raise AppError("Encrypted PDFs are not supported. Upload an unencrypted copy.")
            count = len(reader.pages)
            if not count:
                raise AppError("The PDF contains no pages.")
            if count > MAX_PAGES:
                raise AppError("The PDF exceeds the 200-page limit. Upload a smaller document.")
            document = None
            for index, native_page in enumerate(reader.pages):
                number = index + 1
                text = "" if ocr_mode == "force" else (native_page.extract_text() or "")
                method = "native"
                if ocr_mode == "force" or len(re.sub(r"\s", "", text)) < 40:
                    if document is None:
                        document = resources.enter_context(pdfium.PdfDocument(pdf_bytes))
                    if progress:
                        progress(index / count, f"Reading page {number} of {count} with OCR")
                    text = _ocr_page(document, index)
                    method = "ocr"
                text = text.strip()
                if not text:
                    warnings.append(f"Page {number} has no readable text after extraction and OCR.")
                pages.append(Page(number, text, method))
                if progress:
                    progress(number / count, f"Read page {number} of {count}")
    except AppError:
        raise
    except pytesseract.TesseractNotFoundError as exc:
        raise AppError(
            "OCR needs Tesseract. Install Tesseract with English language data."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise AppError("OCR failed. Check Tesseract and its English language data.") from exc
    except RuntimeError as exc:
        raise AppError(
            "PDF rendering or OCR failed; OCR allows 30 seconds per page. "
            "Try a smaller PDF or check the local Tesseract installation."
        ) from exc
    except Exception as exc:
        raise AppError(
            "The PDF could not be read. Re-export it as a valid, unencrypted PDF."
        ) from exc
    if not any(page.text for page in pages):
        raise AppError("No readable text was found, including after OCR. Try a clearer PDF.")
    return pages, warnings


def chunk_pages(pages: list[Page], settings: Settings) -> list[Chunk]:
    """Split within pages, favoring paragraph boundaries and retaining overlap."""
    chunks = []
    for page in pages:
        text = page.text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[^\S\n]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        start, ordinal = 0, 1
        while start < len(text):
            end = min(start + settings.chunk_size, len(text))
            if end < len(text):
                midpoint = start + settings.chunk_size // 2
                for separator in ("\n\n", "\n", " "):
                    boundary = text.rfind(separator, midpoint, end)
                    if boundary != -1:
                        end = boundary + len(separator)
                        break
            content = text[start:end].strip()
            if content:
                chunks.append(
                    Chunk(f"p{page.number}-c{ordinal}", content, page.number, page.method)
                )
                ordinal += 1
            if end == len(text):
                break
            start = end - settings.overlap
    return chunks
