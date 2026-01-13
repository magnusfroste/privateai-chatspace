import os
import httpx
import aiofiles
import asyncio
from typing import Optional, List
from pathlib import Path
from app.core.config import settings


class DocumentService:
    def __init__(self):
        self.originals_dir = Path(settings.ORIGINALS_DIR)
        self.markdown_dir = Path(settings.MARKDOWN_DIR)
        self.pdf_provider = settings.PDF_PROVIDER.lower()
        self.docling_service_url = settings.DOCLING_SERVICE_URL.rstrip('/') if settings.DOCLING_SERVICE_URL else None
        self.ocr_service_url = settings.OCR_SERVICE_URL.rstrip('/') if settings.OCR_SERVICE_URL else None
        self._ensure_dirs()
        self._docling_converter = None
    
    def _ensure_dirs(self):
        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_original(
        self,
        workspace_id: int,
        filename: str,
        content: bytes
    ) -> str:
        """Save original file and return path"""
        workspace_dir = self.originals_dir / str(workspace_id)
        workspace_dir.mkdir(exist_ok=True)
        
        file_path = workspace_dir / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        return str(file_path)
    
    async def convert_to_markdown(
        self,
        original_path: str,
        workspace_id: int,
        document_id: int
    ) -> str:
        """Convert document to markdown"""
        original = Path(original_path)
        suffix = original.suffix.lower()
        
        content = ""
        
        if suffix == ".txt" or suffix == ".md":
            async with aiofiles.open(original, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()
        
        elif suffix == ".pdf":
            content = await self._convert_pdf(original)
        
        elif suffix == ".docx":
            content = await self._convert_docx(original)
        
        else:
            async with aiofiles.open(original, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()
        
        workspace_md_dir = self.markdown_dir / str(workspace_id)
        workspace_md_dir.mkdir(exist_ok=True)
        
        md_filename = f"{document_id}_{original.stem}.md"
        md_path = workspace_md_dir / md_filename
        
        async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
            await f.write(content)
        
        return str(md_path)
    
    async def _convert_pdf(self, path: Path) -> str:
        """Convert PDF to markdown using configured provider"""
        # Get current provider from settings_service (allows admin override)
        from app.services.settings_service import settings_service
        from app.core.database import async_session
        
        pdf_provider = self.pdf_provider  # default from env
        try:
            async with async_session() as db:
                db_value = await settings_service.get(db, "pdf_provider")
                if db_value:
                    pdf_provider = db_value.lower()
        except Exception:
            pass  # Use env default on error
        
        print(f"[PDF] Converting {path.name} with provider: {pdf_provider}")
        
        if pdf_provider == "docling-api" and self.docling_service_url:
            try:
                result = await self._convert_pdf_with_docling_api(path)
                if result and not result.startswith("Error"):
                    return result
            except Exception as e:
                print(f"Docling API failed, falling back to pdfplumber: {e}")
        
        elif pdf_provider == "marker-api" and self.ocr_service_url:
            try:
                result = await self._convert_pdf_with_marker(path)
                if result and not result.startswith("Error"):
                    return result
            except Exception as e:
                print(f"Marker API failed, falling back to pdfplumber: {e}")
        
        print(f"[PDF] Using pdfplumber for {path.name}")
        return await self._convert_pdf_with_pdfplumber(path)
    
    async def _convert_pdf_with_docling_api(self, path: Path) -> str:
        """Convert PDF to markdown using docling-serve API (GPU-accelerated microservice)
        
        Uses optimized parameters for rich markdown output suitable for RAG:
        - Accurate table extraction with structure preservation
        - OCR for scanned documents
        - Formula extraction (LaTeX)
        - Code block detection
        - Image descriptions via VLM (if enabled on server)
        """
        try:
            import json
            import time
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=600.0) as client:
                async with aiofiles.open(path, "rb") as f:
                    pdf_content = await f.read()
                
                # Optimized parameters for rich RAG-friendly markdown
                parameters = {
                    "options": {
                        "from_formats": ["pdf"],
                        "to_formats": ["md"],
                        
                        # OCR Settings
                        "do_ocr": True,
                        "force_ocr": False,
                        
                        # Table Extraction (critical for RAG)
                        "do_table_structure": True,
                        
                        # Content Enrichment
                        "do_code_enrichment": True,
                        
                        # Image Handling
                        "generate_picture_images": True,
                        
                        # Error Handling
                        "abort_on_error": False,
                    }
                }
                
                files = {"files": (path.name, pdf_content, "application/pdf")}
                data = {"parameters": json.dumps(parameters)}
                
                response = await client.post(
                    f"{self.docling_service_url}/v1alpha/convert/file",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                
                result = response.json()
                duration = time.time() - start_time
                
                if result.get("status") == "success" and result.get("document"):
                    markdown = result["document"].get("md_content", "")
                    if markdown:
                        print(f"Docling processed {path.name} in {duration:.1f}s ({len(markdown)} chars)")
                        return markdown
                    return f"Error: No markdown content in response: {result}"
                else:
                    errors = result.get("errors", [])
                    return f"Error converting PDF with Docling API: {errors}"
        except Exception as e:
            return f"Error converting PDF with Docling API: {e}"
    
    async def _convert_pdf_with_marker(self, path: Path) -> str:
        """Convert PDF to markdown using Marker API (supports OCR)"""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with aiofiles.open(path, "rb") as f:
                    pdf_content = await f.read()
                
                files = {"file": (path.name, pdf_content, "application/pdf")}
                response = await client.post(
                    f"{self.ocr_service_url}/convert",
                    files=files
                )
                response.raise_for_status()
                
                data = response.json()
                if isinstance(data, dict):
                    return data.get("markdown", data.get("text", data.get("content", str(data))))
                return str(data)
        except Exception as e:
            return f"Error converting PDF with Marker: {e}"
    
    async def _convert_pdf_with_pdfplumber(self, path: Path) -> str:
        """Convert PDF to markdown using pdfplumber (better table/layout extraction)"""
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = []
                    
                    # Extract tables first
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if table:
                                # Convert table to markdown format
                                md_table = self._table_to_markdown(table)
                                if md_table:
                                    page_text.append(md_table)
                    
                    # Extract remaining text
                    text = page.extract_text()
                    if text:
                        page_text.append(text)
                    
                    if page_text:
                        text_parts.append("\n\n".join(page_text))
            
            return "\n\n---\n\n".join(text_parts)
        except Exception as e:
            return f"Error converting PDF: {e}"
    
    def _table_to_markdown(self, table: list) -> str:
        """Convert a table (list of rows) to markdown format"""
        if not table or not table[0]:
            return ""
        
        # Clean cells
        cleaned = []
        for row in table:
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            cleaned.append(cleaned_row)
        
        if not cleaned:
            return ""
        
        # Build markdown table
        lines = []
        # Header
        lines.append("| " + " | ".join(cleaned[0]) + " |")
        # Separator
        lines.append("| " + " | ".join(["---"] * len(cleaned[0])) + " |")
        # Data rows
        for row in cleaned[1:]:
            # Pad row if needed
            while len(row) < len(cleaned[0]):
                row.append("")
            lines.append("| " + " | ".join(row[:len(cleaned[0])]) + " |")
        
        return "\n".join(lines)
    
    async def _convert_docx(self, path: Path) -> str:
        """Convert DOCX to markdown"""
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            return f"Error converting DOCX: {e}"
    
    async def read_markdown(self, markdown_path: str) -> str:
        """Read markdown content"""
        async with aiofiles.open(markdown_path, "r", encoding="utf-8") as f:
            return await f.read()
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into semantic chunks that respect document structure.
        
        Strategy:
        1. Split by markdown headers (##, ###) to preserve sections
        2. Keep tables intact (don't split mid-table)
        3. Respect paragraph boundaries
        4. Use overlap for context continuity
        """
        import re
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # First, try to split by major sections (## headers)
        sections = re.split(r'\n(?=## )', text)
        
        for section in sections:
            if len(section) <= chunk_size:
                if section.strip():
                    chunks.append(section.strip())
            else:
                # Section too large, split further by subsections (### headers)
                subsections = re.split(r'\n(?=### )', section)
                
                for subsection in subsections:
                    if len(subsection) <= chunk_size:
                        if subsection.strip():
                            chunks.append(subsection.strip())
                    else:
                        # Subsection still too large, split by paragraphs
                        # but keep tables intact
                        sub_chunks = self._split_preserving_tables(subsection, chunk_size, overlap)
                        chunks.extend(sub_chunks)
        
        return [c for c in chunks if c and len(c) > 50]  # Filter tiny chunks
    
    def _split_preserving_tables(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text while keeping markdown tables intact"""
        import re
        
        chunks = []
        
        # Find all tables in the text
        table_pattern = r'(\|[^\n]+\|\n(?:\|[-:| ]+\|\n)?(?:\|[^\n]+\|\n)*)'
        
        # Split text around tables
        parts = re.split(table_pattern, text)
        
        current_chunk = ""
        for part in parts:
            if not part.strip():
                continue
                
            # Check if this part is a table
            is_table = part.strip().startswith('|') and '|' in part
            
            if is_table:
                # Tables should stay intact
                if len(current_chunk) + len(part) <= chunk_size * 1.5:  # Allow larger chunks for tables
                    current_chunk += part
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = part
            else:
                # Regular text - split by paragraphs if needed
                paragraphs = part.split('\n\n')
                for para in paragraphs:
                    if len(current_chunk) + len(para) <= chunk_size:
                        current_chunk += ('\n\n' if current_chunk else '') + para
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        # Start new chunk with overlap from previous
                        if chunks and overlap > 0:
                            prev_words = chunks[-1].split()[-overlap//10:]  # ~10 chars per word
                            current_chunk = ' '.join(prev_words) + '\n\n' + para
                        else:
                            current_chunk = para
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def delete_files(self, original_path: Optional[str], markdown_path: Optional[str]):
        """Delete document files"""
        for path in [original_path, markdown_path]:
            if path and os.path.exists(path):
                os.remove(path)


document_service = DocumentService()
