import os
import pickle
import numpy as np
from app.core.config import settings

class SkillGraphEmbedder:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self._model = None
        self.index = None
        self.metadata = {}
        self.load_index()

    @property
    def model(self):
        if self._model is None:
            # Set thread limits before loading SentenceTransformer/PyTorch
            import torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            
            print(f"Lazy-initializing embedder with model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def load_index(self) -> bool:
        """Loads the FAISS index and pickle metadata mapping."""
        if os.path.exists(settings.FAISS_INDEX_PATH) and os.path.exists(settings.FAISS_METADATA_PATH):
            try:
                import faiss
                self.index = faiss.read_index(settings.FAISS_INDEX_PATH)
                with open(settings.FAISS_METADATA_PATH, 'rb') as f:
                    self.metadata = pickle.load(f)
                print(f"Loaded FAISS index with {self.index.ntotal} elements.")
                return True
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                self.index = None
                self.metadata = {}
        else:
            print("FAISS index files not found. Vector search will be unavailable until indexed.")
        return False

    def get_embedding(self, text: str) -> np.ndarray:
        """Generates a 384-dimensional embedding for a text query."""
        embedding = self.model.encode([text])[0]  # Returns [[]], so get 0th array and [text] is used instead of just text because encode expects [].
        return np.array(embedding).astype('float32')

    def search_similar(self, query: str, top_k: int = 5, item_type: str = None) -> list:
        """
        Searches the FAISS index for semantically similar nodes.
        Filters by item_type ('Skill' or 'Occupation') if provided.
        """
        if self.index is None:
            # Fallback load attempt
            if not self.load_index():
                print("FAISS index is not initialized. Returning empty.")
                return []
                
        # Embed and normalize query
        # Reshape(1, -1) => means we re-shape the [384,] to [1,384] , 1 means 1 row and -1 means auto-calculate columns
        query_vector = self.get_embedding(query).reshape(1, -1) # FAISS expects a 2D array of shape (number of vectors, dimension of vectors)
        import faiss
        faiss.normalize_L2(query_vector)
        
        # Search index. Since it's IndexFlatIP on normalized vectors, similarity is Cosine similarity
        # Query for more than top_k if we need to filter by type
        search_k = top_k * 4 if item_type else top_k
        search_k = min(search_k, self.index.ntotal)
        
        if search_k == 0:
            return []
            
        similarities, indices = self.index.search(query_vector, search_k)
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata.get(idx)
            if meta:
                if item_type and meta.get("type") != item_type:
                    continue
                results.append({
                    "id": meta["id"],
                    "name": meta["name"],
                    "type": meta["type"],
                    "similarity": float(sim)
                })
                if len(results) >= top_k:
                    break
        return results

# Shared global embedder instance
embedder_instance = SkillGraphEmbedder()
