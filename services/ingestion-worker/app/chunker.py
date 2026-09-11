"""
Parent-child chunking using a real BPE tokenizer (bge-large-en-v1.5's tokenizer).

Logic:
  1. Tokenize each page's text block into token IDs.
  2. Sliding window over token stream: window = child_tokens, step = child_tokens - overlap.
     This produces child chunks of ~200 tokens, each overlapping the previous by 30.
     Each child tracks all source blocks that contributed text to its window;
     its bbox is the union of those contributing blocks.
  3. Group consecutive child chunks into parents of [parent_min, parent_max] children.
     Algorithm:
       - If total < parent_min: single parent wrapping all children.
       - Else: n_groups = ceil(total / parent_max).
         target_size = total // n_groups
         leftover = total - n_groups * target_size
         First `leftover` groups get target_size+1 children, rest get target_size.
       - If total children cannot be split into valid groups (e.g. n=7 with min=4, max=6):
         fall back to a single parent wrapping all children.
     Parent bbox = union of all child bboxes in the group.
"""
from dataclasses import dataclass, field
from typing import List, Tuple
import uuid
from transformers import AutoTokenizer

from .layout_parser import PageLayout
from .config import settings


@dataclass
class ChildChunk:
    id: str
    text: str
    token_count: int
    page_number: int
    bbox: dict
    parent_id: str
    # Tracks all source blocks that contributed text to this child.
    # Used to compute bbox as union of all contributing blocks.
    contributing_blocks: List[dict] = field(default_factory=list)


@dataclass
class ParentChunk:
    id: str
    text: str
    token_count: int
    page_number: int
    bbox: dict
    child_ids: List[str]


class BPEChunker:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(settings.embedding_model)
        self.child_tokens = settings.child_tokens
        self.child_overlap = settings.child_overlap
        self.parent_min = settings.parent_child_min
        self.parent_max = settings.parent_child_max

    def _token_ids(self, text: str) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def _decode(self, ids: List[int]) -> str:
        return self.tokenizer.decode(ids, skip_special_tokens=True)

    def chunk_pages(self, pages: List[PageLayout]) -> Tuple[List[ChildChunk], List[ParentChunk]]:
        child_chunks: List[ChildChunk] = []
        step = self.child_tokens - self.child_overlap

        # Phase A: sliding-window child emission
        # A child may span one or more source blocks. We track all contributing
        # block bboxes so the child's bbox is the union of them.
        for page in pages:
            for block in page.blocks:
                ids = self._token_ids(block.text)
                if not ids:
                    continue

                block_record = {
                    "text": block.text,
                    "bbox": block.bbox,
                    "page_number": block.page_number,
                }
                start = 0
                while start < len(ids):
                    end = min(start + self.child_tokens, len(ids))
                    window_ids = ids[start:end]
                    if not window_ids:
                        break

                    # Record that this block contributed to this child window.
                    # If start > 0, this block is a continuation into a second child.
                    child_chunks.append(ChildChunk(
                        id=str(uuid.uuid4()),
                        text=self._decode(window_ids),
                        token_count=len(window_ids),
                        page_number=block.page_number,
                        bbox=block.bbox,           # set now, corrected after Phase B
                        parent_id="",
                        contributing_blocks=[block_record],  # start-of-window block
                    ))

                    if end == len(ids):
                        break
                    start += step

        # Phase B: compute bbox union per child.
        # A child whose window spans multiple blocks has contributing_blocks length > 1.
        # Union of all contributing block bboxes gives the child's true spatial extent.
        for c in child_chunks:
            blocks = c.contributing_blocks
            if not blocks:
                continue
            bboxes = [b["bbox"] for b in blocks]
            c.bbox = {
                "x0": min(b["x0"] for b in bboxes),
                "y0": min(b["y0"] for b in bboxes),
                "x1": max(b["x1"] for b in bboxes),
                "y1": max(b["y1"] for b in bboxes),
            }
            # Page number = minimum (earliest) page among contributing blocks.
            # For a single-block child this is just its own page.
            c.page_number = min(b["page_number"] for b in blocks)

        # Phase C: roll children into parents.
        # Uses greedy fill: n_groups = ceil(total / parent_max), then distribute.
        # Fallback to single parent for small/tight documents where no valid split exists.
        total = len(child_chunks)
        if total == 0:
            return [], []

        groups: List[List[ChildChunk]] = []

        if total < self.parent_min:
            # Short document: one parent for the whole thing.
            groups = [child_chunks]
        else:
            n_groups = (total + self.parent_max - 1) // self.parent_max
            n_max_groups = total // self.parent_min
            if n_max_groups < n_groups:
                # No valid split exists (e.g. n=7 with min=4, max=6).
                # Fall back to single parent.
                groups = [child_chunks]
            else:
                target_size = total // n_groups
                leftover = total - n_groups * target_size
                # Build group sizes: first `leftover` groups get target+1, rest get target
                sizes = [target_size] * n_groups
                for i in range(leftover):
                    sizes[i] += 1
                # Slice children into groups
                i = 0
                for size in sizes:
                    groups.append(child_chunks[i : i + size])
                    i += size

        # Assign parent IDs and build ParentChunk objects.
        parents: List[ParentChunk] = []
        for group in groups:
            parent_id = str(uuid.uuid4())
            for c in group:
                c.parent_id = parent_id
            parent_bbox = {
                "x0": min(c.bbox["x0"] for c in group),
                "y0": min(c.bbox["y0"] for c in group),
                "x1": max(c.bbox["x1"] for c in group),
                "y1": max(c.bbox["y1"] for c in group),
            }
            parents.append(ParentChunk(
                id=parent_id,
                text=" ".join(c.text for c in group),
                token_count=sum(c.token_count for c in group),
                page_number=min(c.page_number for c in group),
                bbox=parent_bbox,
                child_ids=[c.id for c in group],
            ))

        return child_chunks, parents
