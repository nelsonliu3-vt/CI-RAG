"""
Simple Text Chunker
Splits text into overlapping chunks for indexing
"""

import logging
from typing import List
import tiktoken

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    encoding_name: str = "cl100k_base"
) -> List[str]:
    """
    Chunk text into overlapping segments

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
        encoding_name: Tokenizer encoding name

    Returns:
        List of text chunks
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        # Fallback to simple splitting
        return _chunk_by_chars(text, chunk_size * 4, chunk_overlap * 4)

    # Encode text
    tokens = encoding.encode(text)

    if len(tokens) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

        # Move start with overlap
        start += chunk_size - chunk_overlap

    return chunks


def _chunk_by_chars(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Fallback chunking by characters"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap

    return chunks


if __name__ == "__main__":
    # Test chunker
    test_text = "This is a test. " * 200

    chunks = chunk_text(test_text, chunk_size=100, chunk_overlap=20)

    print(f"✓ Chunked {len(test_text)} chars into {len(chunks)} chunks")
    print(f"  First chunk: {chunks[0][:50]}...")
    print(f"  Last chunk: {chunks[-1][:50]}...")
