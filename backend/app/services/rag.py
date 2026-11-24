import io
import math
import re
from typing import List, Tuple

def extract_text_from_file(filename: str, content_bytes: bytes) -> str:
    ext = filename.lower().split(".")[-1]
    
    if ext in ["txt", "md", "json", "csv"]:
        return content_bytes.decode("utf-8", errors="replace")
        
    elif ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[Page {i+1}]\n{text.strip()}")
            return "\n\n".join(pages) if pages else content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return content_bytes.decode("utf-8", errors="replace")
            
    elif ext == "docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(content_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception:
            return content_bytes.decode("utf-8", errors="replace")
            
    return content_bytes.decode("utf-8", errors="replace")

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]
        
    chunks = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        if end >= len(cleaned):
            chunks.append(cleaned[start:].strip())
            break
        # Try to break on sentence or word boundary
        split_at = cleaned.rfind(". ", start, end)
        if split_at == -1 or split_at <= start:
            split_at = cleaned.rfind(" ", start, end)
        if split_at == -1 or split_at <= start:
            split_at = end
        else:
            split_at += 1
            
        chunk = cleaned[start:split_at].strip()
        if chunk:
            chunks.append(chunk)
        start = max(start + 1, split_at - overlap)
    return chunks

def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))

def generate_embedding(text: str, dim: int = 64) -> List[float]:
    """
    Deterministic semantic hash vector for lightweight, fast similarity matching
    without requiring third-party API keys or massive weights.
    """
    token_list = re.findall(r"[a-z0-9]+", text.lower())
    vec = [0.0] * dim
    if not token_list:
        return vec
    for tok in token_list:
        h = hash(tok)
        idx = abs(h) % dim
        sign = 1.0 if (h >> 3) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [round(v / norm, 4) for v in vec]
    return vec

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    return max(0.0, min(1.0, dot))

def keyword_overlap(query: str, chunk: str) -> float:
    q_words = words(query)
    c_words = words(chunk)
    if not q_words:
        return 0.0
    return len(q_words & c_words) / len(q_words)
