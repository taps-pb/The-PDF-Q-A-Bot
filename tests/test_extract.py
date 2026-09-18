"""Deterministic boundary checks plus an opt-in real Tesseract smoke test."""

from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from pdf_qa.extract import chunk_pages, extract_pages
from pdf_qa.types import AppError, Page, Settings


def make_pdf(texts):
    output = BytesIO()
    document = canvas.Canvas(output)
    for text in texts:
        document.setFont("Helvetica", 18)
        document.drawString(50, 750, text)
        document.showPage()
    document.save()
    return output.getvalue()


def test_native_auto_ocr_blank_pages_and_progress():
    native = "This selectable text is long enough to bypass automatic OCR."
    progress = Mock()
    with patch("pdf_qa.extract._ocr_page", side_effect=["Scanned text", ""]) as ocr:
        pages, warnings = extract_pages(make_pdf([native, "tiny", ""]), progress=progress)
    assert pages == [Page(1, native, "native"), Page(2, "Scanned text", "ocr"), Page(3, "", "ocr")]
    assert [call.args[1] for call in ocr.call_args_list] == [1, 2]
    assert len(warnings) == 1 and "Page 3" in warnings[0]
    assert progress.call_args.args == (1.0, "Read page 3 of 3")


def test_force_ocr_replaces_native_text():
    with patch("pdf_qa.extract._ocr_page", return_value="OCR replacement"):
        pages, _ = extract_pages(make_pdf(["Native text that must not be duplicated."]), "force")
    assert pages == [Page(1, "OCR replacement", "ocr")]


def test_validation_and_no_readable_content():
    for data, message in [(b"", "nonempty"), (b"not a PDF", "not a PDF"), (b"%PDF-", "read")]:
        with pytest.raises(AppError, match=message):
            extract_pages(data)
    with pytest.raises(AppError, match="auto or force"):
        extract_pages(b"%PDF-", "unknown")
    with patch("pdf_qa.extract.MAX_BYTES", 5), pytest.raises(AppError, match="50 MiB"):
        extract_pages(b"%PDF-1.7")
    with patch("pdf_qa.extract.MAX_PAGES", 1), pytest.raises(AppError, match="200-page"):
        extract_pages(make_pdf(["page one", "page two"]))
    with patch("pdf_qa.extract._ocr_page", return_value=" \n"), pytest.raises(
        AppError, match="No readable text"
    ):
        extract_pages(make_pdf([""]))
    output = BytesIO()
    writer = PdfWriter()
    writer.write(output)
    with pytest.raises(AppError, match="no pages"):
        extract_pages(output.getvalue())
    writer.add_blank_page(612, 792)
    writer.encrypt("password")
    output = BytesIO()
    writer.write(output)
    with pytest.raises(AppError, match="Encrypted"):
        extract_pages(output.getvalue())


def test_ocr_limits_and_cleanup():
    data = make_pdf(["tiny"])
    with patch("pdf_qa.extract.MAX_OCR_PIXELS", 10), pytest.raises(AppError, match="pixel"):
        extract_pages(data)
    with patch("pdf_qa.extract.pytesseract.image_to_string") as recognize:
        recognize.side_effect = RuntimeError("Tesseract process timeout")
        with pytest.raises(AppError, match="30 seconds"):
            extract_pages(data)
        assert recognize.call_args.kwargs == {"lang": "eng", "timeout": 30}
        image = recognize.call_args.args[0]
        with pytest.raises(ValueError, match="closed image"):
            image.getpixel((0, 0))


def test_page_boundaries_normalization_and_exact_overlap():
    pages = [Page(2, "a" * 900, "ocr"), Page(4, "  A\t B\r\n\r\n\r\n C  ", "native")]
    chunks = chunk_pages(pages, Settings(chunk_size=300))
    assert [len(chunk.text) for chunk in chunks] == [300, 300, 300, 180, 6]
    assert chunks[-1].text == "A B\n\nC"
    assert [chunk.id for chunk in chunks] == ["p2-c1", "p2-c2", "p2-c3", "p2-c4", "p4-c1"]
    assert all(chunk.page == 2 and chunk.method == "ocr" for chunk in chunks[:-1])
    assert chunk_pages([Page(1, " \n\t ", "native")], Settings()) == []
    text = "".join(str(index % 10) for index in range(701))
    chunks = chunk_pages([Page(1, text, "native")], Settings(chunk_size=300))
    assert chunks[0].text == text[:300]
    assert chunks[1].text == text[240:540]
    assert chunks[2].text == text[480:]


def test_paragraph_then_line_then_word_boundaries():
    for separator in ("\n\n", "\n", " "):
        text = "a" * 200 + separator + "b" * 200
        chunks = chunk_pages([Page(1, text, "native")], Settings(chunk_size=300))
        assert chunks[0].text == "a" * 200
        assert all(0 < len(chunk.text) <= 300 for chunk in chunks)
        assert chunks[-1].text.endswith("b" * 200)


@pytest.mark.integration
def test_real_english_ocr():
    # Force rendering so this verifies the same OCR path used for scanned pages.
    pages, warnings = extract_pages(make_pdf(["LOCAL OCR TEST NUMBER 12345"]), "force")
    assert "LOCAL OCR TEST NUMBER 12345" in pages[0].text
    assert pages[0].method == "ocr"
    assert not warnings
