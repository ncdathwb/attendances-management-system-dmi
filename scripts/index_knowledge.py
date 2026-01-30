"""
Indexer cho chatbot: quét các file giao diện/nghiệp vụ, tạo embedding và lưu vào
Chroma (persistent) để chatbot truy vấn RAG.

Chạy:
    python scripts/index_knowledge.py

Env optional:
    CHATBOT_KB_PATH: thư mục lưu vector store (default: state/knowledge)
    CHATBOT_KB_COLLECTION: tên collection (default: dmi_knowledge)
    CHATBOT_EMBED_MODEL: model sentence-transformers (default: sentence-transformers/all-MiniLM-L6-v2)
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Iterable, List, Tuple

import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent

CHATBOT_KB_PATH = os.environ.get("CHATBOT_KB_PATH", str(ROOT / "state" / "knowledge"))
CHATBOT_KB_COLLECTION = os.environ.get("CHATBOT_KB_COLLECTION", "dmi_knowledge")
CHATBOT_EMBED_MODEL = os.environ.get(
    "CHATBOT_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# Các file ưu tiên (gần giao diện & nghiệp vụ hướng dẫn)
DEFAULT_FILES = [
    ROOT / "templates" / "leave_request_form.html",
    ROOT / "templates" / "leave_requests_list.html",
    ROOT / "templates" / "leave_history.html",
    ROOT / "templates" / "settings.html",
    ROOT / "templates" / "dashboard.html",
    ROOT / "app.py",  # chứa mô tả quy trình/phê duyệt
]


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Loại bỏ thẻ HTML đơn giản để giảm nhiễu
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    # Nén khoảng trắng
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200) -> List[str]:
    """Chia text thành các đoạn có độ dài vừa phải (theo ký tự)."""
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
    return chunks


def collect_chunks(files: Iterable[Path]) -> List[Tuple[str, str]]:
    """Trả về list (path_str, chunk_text)."""
    output: List[Tuple[str, str]] = []
    for p in files:
        if not p.exists():
            continue
        try:
            txt = read_text(p)
        except Exception as e:
            print(f"[index] Bỏ qua {p}: {e}")
            continue
        for chunk in chunk_text(txt):
            if chunk:
                output.append((str(p.relative_to(ROOT)), chunk))
    return output


def build_embeddings(model_name: str, texts: List[str]) -> List[List[float]]:
    print(f"[index] Load embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    # Chuẩn hóa để phù hợp cosine
    return model.encode(texts, normalize_embeddings=True).tolist()


def main():
    files = DEFAULT_FILES
    chunks = collect_chunks(files)
    if not chunks:
        print("[index] Không có dữ liệu để index.")
        return

    docs = [c[1] for c in chunks]
    metas = [{"path": c[0]} for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]

    embeddings = build_embeddings(CHATBOT_EMBED_MODEL, docs)

    # Khởi tạo Chroma persistent
    client = chromadb.PersistentClient(path=CHATBOT_KB_PATH)
    coll = client.get_or_create_collection(name=CHATBOT_KB_COLLECTION)

    # Xóa dữ liệu cũ rồi nạp mới để tránh trùng lặp
    coll.delete(where={})
    coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    print(f"[index] Đã index {len(docs)} chunks vào {CHATBOT_KB_PATH}/{CHATBOT_KB_COLLECTION}")


if __name__ == "__main__":
    main()

