"""Small records shared by extraction, retrieval, the UI, and evaluation."""

from dataclasses import dataclass


class AppError(Exception):
    """An actionable failure that can safely be shown to the user."""


@dataclass(frozen=True)
class Settings:
    chunk_size: int = 800
    overlap: int = 60
    ocr_mode: str = "auto"

    def __post_init__(self):
        if self.chunk_size not in (300, 800, 1500):
            raise AppError("Choose a chunk size of 300, 800, or 1500 characters.")
        if self.overlap != 60:
            raise AppError("Chunk overlap must be 60 characters for this experiment.")
        if self.ocr_mode not in ("auto", "force"):
            raise AppError("Extraction mode must be auto or force.")


@dataclass(frozen=True)
class Page:
    number: int
    text: str
    method: str


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    page: int
    method: str


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[int]
    chunk_ids: list[str]
    refused: bool
