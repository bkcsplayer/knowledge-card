"""
Embedding Service for Knowledge Distillery
Generates vector embeddings for semantic search using OpenRouter
"""

import httpx
import logging
from typing import List, Optional
import numpy as np

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings
    Uses OpenRouter API with embedding models
    """
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        # Use a smaller model for embeddings (1536 dimensions)
        self.embedding_model = "openai/text-embedding-3-small"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://knowledge-distillery.local",
            "X-Title": "Knowledge Distillery"
        }
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text
        
        Args:
            text: Text to generate embedding for
        
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        if not settings.ai_configured:
            logger.warning("AI not configured - cannot generate embeddings")
            return None
        
        # Truncate text if too long (max ~8000 tokens)
        text = text[:30000] if len(text) > 30000 else text
        
        payload = {
            "model": self.embedding_model,
            "input": text
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract embedding from response
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0]["embedding"]
                
                logger.error(f"Unexpected embedding response: {data}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to generate embeddings for
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Global embedding service instance
embedding_service = EmbeddingService()

