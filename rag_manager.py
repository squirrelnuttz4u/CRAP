# rag_manager.py
# © 2025 Colt McVey
# The Retrieval-Augmented Generation (RAG) system for project context.

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import logging

from llm_interface import InferenceEngine
from settings_manager import settings_manager

# --- Simple Text Chunking ---
def chunk_text(text: str, chunk_size=512, overlap=50) -> List[str]:
    """Splits text into overlapping chunks."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

# --- In-Memory Vector Store ---
class VectorStore:
    """A simple in-memory vector store using NumPy."""
    def __init__(self):
        self.vectors = []
        self.metadata = [] # Stores info like file_path and original chunk text

    def add(self, vector: np.ndarray, meta: Dict):
        """Adds a vector and its metadata to the store."""
        self.vectors.append(vector)
        self.metadata.append(meta)

    def search(self, query_vector: np.ndarray, top_k=3) -> List[Dict]:
        """Finds the top_k most similar vectors."""
        if not self.vectors:
            return []
        
        # Stack vectors into a single NumPy array for efficient computation
        vector_matrix = np.vstack(self.vectors)
        
        # Calculate cosine similarity between the query and all stored vectors
        similarities = cosine_similarity(query_vector.reshape(1, -1), vector_matrix)[0]
        
        # Get the indices of the top_k most similar vectors
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [self.metadata[i] for i in top_k_indices]

    def clear(self):
        """Clears the entire vector store."""
        self.vectors = []
        self.metadata = []

# --- RAG Manager Service ---
class RAGManager:
    """Orchestrates the chunking, embedding, and retrieval process."""
    def __init__(self):
        self.engine = InferenceEngine()
        self.vector_store = VectorStore()
        self.embedding_model = "nomic-embed-text" # A good default embedding model
        self.is_indexing = False

    async def index_files(self, files: List[Dict]):
        """Chunks and embeds a list of files, adding them to the vector store."""
        if self.is_indexing:
            logging.warning("Indexing is already in progress.")
            return
            
        self.is_indexing = True
        self.vector_store.clear()
        logging.info(f"Starting indexing for {len(files)} files...")

        for file_info in files:
            file_path = file_info['path']
            content = file_info['content']
            chunks = chunk_text(content)
            
            for chunk in chunks:
                try:
                    embedding = await self.engine.embed(self.embedding_model, chunk)
                    if embedding:
                        meta = {"file_path": file_path, "content": chunk}
                        self.vector_store.add(np.array(embedding), meta)
                except Exception as e:
                    logging.error(f"Failed to create embedding for chunk from {file_path}: {e}")
        
        logging.info(f"Indexing complete. Vector store contains {len(self.vector_store.vectors)} chunks.")
        self.is_indexing = False

    async def retrieve_context(self, query: str, top_k=3) -> List[Dict]:
        """Retrieves the most relevant context for a given query."""
        if self.is_indexing or not self.vector_store.vectors:
            return []
            
        try:
            query_embedding = await self.engine.embed(self.embedding_model, query)
            if query_embedding:
                return self.vector_store.search(np.array(query_embedding), top_k=top_k)
        except Exception as e:
            logging.error(f"Failed to retrieve context for query '{query}': {e}")
        
        return []

# --- Global Instance ---
rag_manager = RAGManager()
