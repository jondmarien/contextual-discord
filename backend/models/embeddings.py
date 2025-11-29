from sentence_transformers import SentenceTransformer
import time

class EmbeddingModel:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded.")
    
    def encode(self, text):
        start_time = time.time()
        embedding = self.model.encode(text)
        duration = (time.time() - start_time) * 1000
        return embedding.tolist(), duration
