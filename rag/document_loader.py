
from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "rag" / "documents"
SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def load_documents(directory: Path | None = None) -> list[dict[str, str]]:
    """Load text from PDF and TXT files in the documents directory."""
    source_dir = directory or DOCUMENTS_DIR
    documents: list[dict[str, str]] = []

    if not source_dir.exists():
        return documents

    for file_path in sorted(source_dir.iterdir()):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            if file_path.suffix.lower() == ".pdf":
                reader = PdfReader(str(file_path))
                pages = []

                for page_number, page in enumerate(reader.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if text:
                        pages.append(f"[Page {page_number}]\n{text}")

                extracted_text = "\n\n".join(pages).strip()
            else:
                extracted_text = file_path.read_text(
                    encoding="utf-8-sig"
                ).strip()

            if extracted_text:
                documents.append(
                    {
                        "source": file_path.name,
                        "text": extracted_text,
                    }
                )
            else:
                print(f"Warning: No extractable text in {file_path.name}")

        except Exception as exc:
            print(f"Warning: Could not read {file_path.name}: {exc}")

    return documents


def load_pdf_documents(directory: Path | None = None) -> list[dict[str, str]]:
    """Backward-compatible wrapper for the existing PDF loader."""
    return [
        document
        for document in load_documents(directory)
        if document["source"].lower().endswith(".pdf")
    ]


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """Split text into overlapping character-based chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks
