"""
Knowledge Base Loader Script
Loads Word documents into the vector store for RAG.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List

import docx2txt
from docx import Document
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.services.knowledge_base import KnowledgeBaseService


class KnowledgeLoader:
    """Loads documents into the knowledge base."""

    def __init__(self):
        self.kb_service = KnowledgeBaseService()
        self.chunk_size = 1000  # characters per chunk
        self.chunk_overlap = 200  # overlap between chunks

    def read_docx(self, file_path: str) -> str:
        """Read text from a Word document."""
        try:
            # Try docx2txt first (handles more formats)
            text = docx2txt.process(file_path)
            if text:
                return text.strip()
            
            # Fallback to python-docx
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return ""

    def chunk_text(self, text: str, source: str) -> List[dict]:
        """Split text into chunks for embedding."""
        chunks = []
        
        # Clean the text
        text = text.strip()
        if not text:
            return chunks
        
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": {"source": source}
                    })
                
                # If paragraph itself is too long, split it
                if len(para) > self.chunk_size:
                    words = para.split()
                    current_chunk = ""
                    for word in words:
                        if len(current_chunk) + len(word) > self.chunk_size:
                            if current_chunk:
                                chunks.append({
                                    "content": current_chunk.strip(),
                                    "metadata": {"source": source}
                                })
                            current_chunk = word + " "
                        else:
                            current_chunk += word + " "
                else:
                    current_chunk = para + "\n\n"
            else:
                current_chunk += para + "\n\n"
        
        # Add remaining chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": {"source": source}
            })
        
        return chunks

    async def load_directory(self, directory: str, clear_existing: bool = False):
        """Load all Word documents from a directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return
        
        # Find all Word documents
        docx_files = list(dir_path.glob("*.docx")) + list(dir_path.glob("*.doc"))
        
        if not docx_files:
            logger.warning(f"No Word documents found in {directory}")
            return
        
        logger.info(f"Found {len(docx_files)} Word documents")
        
        # Clear existing if requested
        if clear_existing:
            logger.info("Clearing existing knowledge base...")
            await self.kb_service.clear_all()
        
        # Process each file
        total_chunks = 0
        for file_path in docx_files:
            logger.info(f"Processing: {file_path.name}")
            
            # Read document
            text = self.read_docx(str(file_path))
            if not text:
                logger.warning(f"No text extracted from {file_path.name}")
                continue
            
            # Chunk the text
            chunks = self.chunk_text(text, file_path.name)
            logger.info(f"  Created {len(chunks)} chunks")
            
            # Insert chunks
            for i, chunk in enumerate(chunks):
                success = await self.kb_service.add_document(
                    content=chunk["content"],
                    metadata=chunk["metadata"]
                )
                if success:
                    total_chunks += 1
                else:
                    logger.warning(f"  Failed to insert chunk {i+1}")
            
            logger.info(f"  Inserted {len(chunks)} chunks from {file_path.name}")
        
        logger.info(f"✅ Knowledge base loaded: {total_chunks} total chunks")

    async def load_single_file(self, file_path: str):
        """Load a single Word document."""
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        logger.info(f"Processing: {path.name}")
        
        # Read document
        text = self.read_docx(str(path))
        if not text:
            logger.error(f"No text extracted from {path.name}")
            return
        
        # Chunk and insert
        chunks = self.chunk_text(text, path.name)
        logger.info(f"Created {len(chunks)} chunks")
        
        inserted = 0
        for chunk in chunks:
            success = await self.kb_service.add_document(
                content=chunk["content"],
                metadata=chunk["metadata"]
            )
            if success:
                inserted += 1
        
        logger.info(f"✅ Inserted {inserted}/{len(chunks)} chunks")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load knowledge base from Word documents")
    parser.add_argument(
        "path",
        help="Path to a Word document or directory containing Word documents"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing knowledge base before loading"
    )
    
    args = parser.parse_args()
    
    loader = KnowledgeLoader()
    path = Path(args.path)
    
    if path.is_dir():
        await loader.load_directory(str(path), clear_existing=args.clear)
    elif path.is_file():
        if args.clear:
            await loader.kb_service.clear_all()
        await loader.load_single_file(str(path))
    else:
        logger.error(f"Invalid path: {args.path}")


if __name__ == "__main__":
    asyncio.run(main())
