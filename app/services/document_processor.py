"""
Document processing service for chunking and preparing documents for vector storage.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from uuid import uuid4
import io
import json

from langchain.text_splitter import RecursiveCharacterTextSplitter

# PDF and DOCX processing
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


@dataclass
class DocumentChunk:
    """A chunk of a processed document."""

    id: str
    content: str
    metadata: Dict[str, Any]


class DocumentProcessor:
    """
    Processes documents into chunks suitable for vector storage.

    Supports:
    - Plain text
    - Markdown
    - PDF files
    - DOCX files
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def process_text(
        self,
        text: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Process plain text into chunks.

        Args:
            text: The text content
            document_id: Unique identifier for the document
            metadata: Additional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects
        """
        if not text.strip():
            return []

        base_metadata = metadata or {}
        chunks = self.text_splitter.split_text(text)

        return [
            DocumentChunk(
                id=f"{document_id}_chunk_{i}",
                content=chunk,
                metadata={
                    **base_metadata,
                    "document_id": document_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            for i, chunk in enumerate(chunks)
        ]

    def process_pdf(
        self,
        pdf_content: bytes,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Process a PDF file into chunks.

        Args:
            pdf_content: Raw PDF bytes
            document_id: Unique identifier for the document
            metadata: Additional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects
        """
        if PdfReader is None:
            raise ImportError("pypdf is required for PDF processing")

        reader = PdfReader(io.BytesIO(pdf_content))
        base_metadata = metadata or {}

        all_chunks = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if not page_text.strip():
                continue

            page_metadata = {
                **base_metadata,
                "page_number": page_num + 1,
                "total_pages": len(reader.pages),
            }

            chunks = self.text_splitter.split_text(page_text)
            for i, chunk in enumerate(chunks):
                all_chunks.append(
                    DocumentChunk(
                        id=f"{document_id}_page{page_num + 1}_chunk_{i}",
                        content=chunk,
                        metadata={
                            **page_metadata,
                            "document_id": document_id,
                            "chunk_index": len(all_chunks),
                        },
                    )
                )

        # Update total_chunks in metadata
        for chunk in all_chunks:
            chunk.metadata["total_chunks"] = len(all_chunks)

        return all_chunks

    def process_docx(
        self,
        docx_content: bytes,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Process a DOCX file into chunks.

        Args:
            docx_content: Raw DOCX bytes
            document_id: Unique identifier for the document
            metadata: Additional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects
        """
        if DocxDocument is None:
            raise ImportError("python-docx is required for DOCX processing")

        doc = DocxDocument(io.BytesIO(docx_content))
        base_metadata = metadata or {}

        # Extract all paragraphs
        full_text = "\n\n".join(
            paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()
        )

        if not full_text.strip():
            return []

        return self.process_text(full_text, document_id, base_metadata)

    def process_json(
        self,
        json_content: bytes,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Process a JSON file into chunks.
        Handles both arrays of objects and single objects.
        Extracts text from string fields recursively.

        Args:
            json_content: Raw JSON bytes
            document_id: Unique identifier for the document
            metadata: Additional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects
        """
        data = json.loads(json_content.decode("utf-8"))
        base_metadata = metadata or {}

        def extract_text_from_obj(obj, prefix: str = "") -> List[str]:
            """Recursively extract text from JSON objects."""
            texts = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, str) and len(value) > 10:
                        texts.append(f"{new_prefix}: {value}")
                    elif isinstance(value, (dict, list)):
                        texts.extend(extract_text_from_obj(value, new_prefix))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    texts.extend(extract_text_from_obj(item, f"{prefix}[{i}]"))
            return texts

        # Handle array of items (process each as separate entry)
        if isinstance(data, list):
            all_chunks = []
            for idx, item in enumerate(data):
                item_texts = extract_text_from_obj(item)
                if item_texts:
                    item_text = "\n".join(item_texts)
                    item_metadata = {**base_metadata, "json_index": idx}
                    chunks = self.process_text(item_text, f"{document_id}_item{idx}", item_metadata)
                    # Renumber chunk IDs to be unique
                    for chunk in chunks:
                        chunk.id = f"{document_id}_chunk_{len(all_chunks)}"
                        all_chunks.append(chunk)
            # Update total chunks
            for chunk in all_chunks:
                chunk.metadata["total_chunks"] = len(all_chunks)
            return all_chunks
        else:
            # Single object
            texts = extract_text_from_obj(data)
            full_text = "\n".join(texts)
            return self.process_text(full_text, document_id, base_metadata)

    def process_file(
        self,
        content: bytes,
        filename: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Process a file based on its extension.

        Args:
            content: Raw file bytes
            filename: Original filename (used to determine type)
            document_id: Unique identifier for the document
            metadata: Additional metadata to attach to chunks

        Returns:
            List of DocumentChunk objects
        """
        file_metadata = {**(metadata or {}), "filename": filename}
        extension = filename.lower().split(".")[-1]

        if extension == "pdf":
            return self.process_pdf(content, document_id, file_metadata)
        elif extension == "docx":
            return self.process_docx(content, document_id, file_metadata)
        elif extension == "json":
            return self.process_json(content, document_id, file_metadata)
        elif extension in ["txt", "md", "markdown"]:
            text = content.decode("utf-8")
            return self.process_text(text, document_id, file_metadata)
        else:
            # Try to process as plain text for unknown extensions
            try:
                text = content.decode("utf-8")
                return self.process_text(text, document_id, file_metadata)
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported file type: {extension}")

    def to_vector_documents(
        self,
        chunks: List[DocumentChunk],
    ) -> List[Dict[str, Any]]:
        """
        Convert DocumentChunks to the format expected by VectorStoreService.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of dicts ready for vector store upsert
        """
        return [
            {
                "id": chunk.id,
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]


# Singleton instance
_document_processor: DocumentProcessor | None = None


def get_document_processor() -> DocumentProcessor:
    """Get the singleton document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
