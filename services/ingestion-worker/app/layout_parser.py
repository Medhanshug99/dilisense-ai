"""
Extracts text + bounding boxes from a PDF using PyMuPDF (fitz).
Returns a list of dicts: {page_number, width, height, blocks}
where each block is {text, bbox: {x0,y0,x1,y2,x2,y3,x3,y4}, lines}.

Also exposes a sanity check: scanned / image-only PDFs produce very little
extractable text. We catch that here so the worker can flag the document
instead of marking it `done` with empty chunks.
"""
import fitz
from dataclasses import dataclass
from typing import List


# Threshold: < 50 chars of text per page on average → likely scanned/image-only.
# Tunable. Real documents with text typically have 1500-3000 chars/page.
MIN_CHARS_PER_PAGE = 50


@dataclass
class TextBlock:
    text: str
    bbox: dict          # {x0, y0, x1, y1}  (PDF coords, bottom-left origin)
    page_number: int


@dataclass
class PageLayout:
    page_number: int
    width: float
    height: float
    blocks: List[TextBlock]


@dataclass
class SanityCheck:
    total_chars: int
    page_count: int
    chars_per_page: float
    is_likely_scanned: bool
    reason: str = ""

    @property
    def is_ok(self) -> bool:
        return not self.is_likely_scanned


def extract_pages(pdf_path: str) -> List[PageLayout]:
    """
    Reads a PDF and returns per-page layout with text blocks and bounding boxes.
    Uses PyMuPDF's block-level text extraction for better structure than raw spans.
    """
    layouts: List[PageLayout] = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            width = page.rect.width
            height = page.rect.height

            # block = dict with 'type', 'bbox', 'lines' (each line has 'spans')
            blocks_out: List[TextBlock] = []
            for block in page.get_text("dict")["blocks"]:
                if block["type"] != 0:          # 0 = text block; skip images/other
                    continue
                for line in block.get("lines", []):
                    spans_text = " ".join(span["text"] for span in line.get("spans", []))
                    if not spans_text.strip():
                        continue
                    raw_bbox = line["bbox"]      # [x0, y0, x1, y1]
                    blocks_out.append(TextBlock(
                        text=spans_text,
                        bbox={"x0": raw_bbox[0], "y0": raw_bbox[1],
                              "x1": raw_bbox[2], "y1": raw_bbox[3]},
                        page_number=page_num,
                    ))

            layouts.append(PageLayout(
                page_number=page_num,
                width=width,
                height=height,
                blocks=blocks_out,
            ))

    return layouts


def sanity_check(pages: List[PageLayout]) -> SanityCheck:
    """
    Heuristic check for scanned / image-only PDFs.
    Counts total extracted chars; compares to page count.
    """
    page_count = len(pages)
    total_chars = sum(
        len(block.text) for page in pages for block in page.blocks
    )
    chars_per_page = total_chars / page_count if page_count else 0.0

    if page_count == 0:
        return SanityCheck(
            total_chars=0, page_count=0, chars_per_page=0.0,
            is_likely_scanned=True,
            reason="PDF has 0 pages",
        )

    if chars_per_page < MIN_CHARS_PER_PAGE:
        return SanityCheck(
            total_chars=total_chars,
            page_count=page_count,
            chars_per_page=chars_per_page,
            is_likely_scanned=True,
            reason=(
                f"Only {chars_per_page:.1f} chars/page extracted "
                f"(threshold {MIN_CHARS_PER_PAGE}). "
                "Document is likely scanned or image-only; OCR not yet supported."
            ),
        )

    return SanityCheck(
        total_chars=total_chars,
        page_count=page_count,
        chars_per_page=chars_per_page,
        is_likely_scanned=False,
    )
