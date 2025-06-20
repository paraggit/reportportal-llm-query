from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import pickle
import hashlib

from loguru import logger
import openai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ..utils.config import Config
from ..models.test_execution import TestExecution


class EmbeddingsManager:
    """Manage embeddings for semantic search and similarity matching"""
    
    def __init__(self, config: Config):
        self.config = config
        self.embeddings_cache_dir = Path(config.cache.directory) / "embeddings"
        self.embeddings_cache_dir.mkdir(exist_ok=True)
        
        # Initialize embedding model based on provider
        if config.llm.provider == "openai":
            self.use_openai = True
            self.embedding_model = "text-embedding-ada-002"
        else:
            self.use_openai = False
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def get_embedding(self, text: str, cache_key: Optional[str] = None) -> np.ndarray:
        """Get embedding for a text string"""
        # Check cache first
        if cache_key:
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                return cached
        
        try:
            if self.use_openai:
                response = openai.Embedding.create(
                    model=self.embedding_model,
                    input=text
                )
                embedding = np.array(response['data'][0]['embedding'])
            else:
                embedding = self.embedding_model.encode(text)
            
            # Cache the result
            if cache_key:
                self._save_to_cache(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def get_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings for multiple texts"""
        embeddings = []
        
        if self.use_openai:
            # OpenAI supports batch processing
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                try:
                    response = openai.Embedding.create(
                        model=self.embedding_model,
                        input=batch
                    )
                    batch_embeddings = [
                        np.array(item['embedding']) 
                        for item in response['data']
                    ]
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"Error in batch embedding: {e}")
                    # Fallback to individual embeddings
                    for text in batch:
                        embeddings.append(self.get_embedding(text))
        else:
            # Sentence transformers handle batching internally
            embeddings = self.embedding_model.encode(texts)
        
        return embeddings
    
    def create_test_embeddings(
        self, 
        test_executions: List[TestExecution]
    ) -> Dict[str, np.ndarray]:
        """Create embeddings for test executions"""
        test_embeddings = {}
        
        for test in test_executions:
            # Create a text representation of the test
            test_text = self._create_test_text(test)
            
            # Generate cache key
            cache_key = self._generate_cache_key(test_text)
            
            # Get embedding
            embedding = self.get_embedding(test_text, cache_key)
            test_embeddings[test.id] = embedding
        
        return test_embeddings
    
    def find_similar_tests(
        self,
        query_embedding: np.ndarray,
        test_embeddings: Dict[str, np.ndarray],
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """Find tests similar to the query"""
        similarities = []
        
        for test_id, test_embedding in test_embeddings.items():
            similarity = cosine_similarity(
                [query_embedding],
                [test_embedding]
            )[0][0]
            
            if similarity >= threshold:
                similarities.append((test_id, float(similarity)))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def cluster_similar_failures(
        self,
        test_executions: List[TestExecution],
        similarity_threshold: float = 0.8
    ) -> List[List[TestExecution]]:
        """Cluster tests with similar failure patterns"""
        failed_tests = [
            test for test in test_executions 
            if test.status == "FAILED" and test.issue
        ]
        
        if not failed_tests:
            return []
        
        # Create embeddings for failure messages
        failure_texts = [
            f"{test.name} {test.issue.comment or ''}"
            for test in failed_tests
        ]
        
        embeddings = self.get_batch_embeddings(failure_texts)
        
        # Simple clustering based on similarity
        clusters = []
        clustered_indices = set()
        
        for i, embedding_i in enumerate(embeddings):
            if i in clustered_indices:
                continue
            
            cluster = [failed_tests[i]]
            clustered_indices.add(i)
            
            for j, embedding_j in enumerate(embeddings):
                if j <= i or j in clustered_indices:
                    continue
                
                similarity = cosine_similarity(
                    [embedding_i],
                    [embedding_j]
                )[0][0]
                
                if similarity >= similarity_threshold:
                    cluster.append(failed_tests[j])
                    clustered_indices.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _create_test_text(self, test: TestExecution) -> str:
        """Create text representation of a test for embedding"""
        parts = [
            f"Test: {test.name}",
            f"Status: {test.status}",
            f"Platform: {test.attributes.get('platform', 'unknown')}",
            f"Owner: {test.attributes.get('owner', 'unknown')}",
        ]
        
        if test.issue and test.issue.comment:
            parts.append(f"Error: {test.issue.comment[:500]}")
        
        if test.description:
            parts.append(f"Description: {test.description[:200]}")
        
        if test.tags:
            parts.append(f"Tags: {', '.join(test.tags)}")
        
        return " | ".join(parts)
    
    def _generate_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _save_to_cache(self, key: str, embedding: np.ndarray):
        """Save embedding to cache"""
        cache_file = self.embeddings_cache_dir / f"{key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
    
    def _load_from_cache(self, key: str) -> Optional[np.ndarray]:
        """Load embedding from cache"""
        cache_file = self.embeddings_cache_dir / f"{key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")
        
        return None