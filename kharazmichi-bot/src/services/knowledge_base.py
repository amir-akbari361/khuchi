"""
Knowledge base service for RAG (Retrieval Augmented Generation).
"""

from typing import List, Optional

from loguru import logger
from openai import OpenAI

from src.config import settings
from src.database.models import KnowledgeSearchResult
from src.database.repositories import KnowledgeRepository


class KnowledgeBaseService:
    """Service for knowledge base operations."""

    def __init__(
        self,
        knowledge_repo: Optional[KnowledgeRepository] = None,
        openai_client: Optional[OpenAI] = None
    ):
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()
        self.openai_client = openai_client or OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = "text-embedding-3-small"

    async def search(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[KnowledgeSearchResult]:
        """
        Search knowledge base for relevant documents.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of relevant knowledge chunks
        """
        try:
            # Generate embedding for query
            query_embedding = await self._get_embedding(query)
            
            if not query_embedding:
                return []

            # Search in vector store
            results = await self.knowledge_repo.search(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )

            logger.debug(f"Found {len(results)} relevant documents for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def add_document(
        self,
        content: str,
        metadata: dict = None
    ) -> bool:
        """
        Add a document to the knowledge base.
        
        Args:
            content: Document content
            metadata: Optional metadata (source, title, etc.)
            
        Returns:
            Success status
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(content)
            
            if not embedding:
                return False

            # Insert into database
            return await self.knowledge_repo.insert(
                content=content,
                embedding=embedding,
                metadata=metadata or {}
            )

        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False

    async def clear_all(self) -> bool:
        """Clear all documents from knowledge base."""
        return await self.knowledge_repo.delete_all()

    def format_context(
        self,
        results: List[KnowledgeSearchResult],
        max_length: int = 3000
    ) -> str:
        """
        Format search results into context string for the AI.
        
        Args:
            results: Search results
            max_length: Maximum context length in characters
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_parts = []
        total_length = 0

        for result in results:
            content = result.content.strip()
            
            # Add source info if available
            source = result.metadata.get("source", "")
            if source:
                content = f"[منبع: {source}]\n{content}"

            if total_length + len(content) > max_length:
                # Truncate if too long
                remaining = max_length - total_length
                if remaining > 100:
                    content = content[:remaining] + "..."
                    context_parts.append(content)
                break

            context_parts.append(content)
            total_length += len(content) + 10  # Account for separators

        return "\n\n---\n\n".join(context_parts)
