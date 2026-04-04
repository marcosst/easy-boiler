"""Split subtitle text into overlapping chunks by line count."""

import re
from dataclasses import dataclass

TIMESTAMP_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)")

CHUNK_LINES = 40  # lines per chunk
OVERLAP_LINES = 5  # overlap lines between chunks


@dataclass
class ChunkResult:
    chunk_text: str  # original lines with [HH:MM:SS] — sent to LLM
    embed_text: str  # text without timestamps — used for embedding
    chunk_index: int
    timestamp_start: str | None
    timestamp_end: str | None


def _extract_timestamp(line: str) -> str | None:
    m = TIMESTAMP_RE.match(line)
    return m.group(1) if m else None


def _strip_timestamp(line: str) -> str:
    m = TIMESTAMP_RE.match(line)
    return m.group(2) if m else line


def chunk_subtitle(text: str) -> list[ChunkResult]:
    """Split subtitle text into chunks of CHUNK_LINES lines with OVERLAP_LINES overlap.

    Each chunk preserves the original lines with timestamps intact,
    so the LLM can reference exact moments.
    """
    raw_lines = [l for l in text.splitlines() if l.strip()]
    if not raw_lines:
        return []

    chunks: list[ChunkResult] = []
    start = 0

    while start < len(raw_lines):
        end = min(start + CHUNK_LINES, len(raw_lines))
        chunk_lines = raw_lines[start:end]

        # Find first and last timestamps in this chunk
        ts_start = None
        ts_end = None
        for line in chunk_lines:
            ts = _extract_timestamp(line)
            if ts:
                if ts_start is None:
                    ts_start = ts
                ts_end = ts

        chunks.append(ChunkResult(
            chunk_text="\n".join(chunk_lines),
            embed_text=" ".join(_strip_timestamp(l) for l in chunk_lines),
            chunk_index=len(chunks),
            timestamp_start=ts_start,
            timestamp_end=ts_end,
        ))

        if end >= len(raw_lines):
            break
        start = end - OVERLAP_LINES

    return chunks
