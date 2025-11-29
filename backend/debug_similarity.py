from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sys

def check_similarity(text1, text2):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    embedding1 = model.encode([text1])
    embedding2 = model.encode([text2])
    
    score = cosine_similarity(embedding1, embedding2)[0][0]
    print(f"Similarity between '{text1}' and '{text2}': {score:.4f}")

if __name__ == "__main__":
    check_similarity("coding frustration", "programming anger")
