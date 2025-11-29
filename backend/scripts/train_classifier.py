import sys
import os
import joblib
import numpy as np
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from tqdm import tqdm

# Add backend to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.embeddings import EmbeddingModel

# GoEmotions Labels
LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", 
    "confusion", "curiosity", "desire", "disappointment", "disapproval", 
    "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief", 
    "joy", "love", "nervousness", "optimism", "pride", "realization", 
    "relief", "remorse", "sadness", "surprise", "neutral"
]

def train():
    print("Loading Embedding Model...")
    embedder = EmbeddingModel()
    
    print("Loading GoEmotions dataset...")
    # Using a subset for speed (first 10k)
    dataset = load_dataset("go_emotions", split="train[:10000]")
    
    print(f"Loaded {len(dataset)} examples.")
    
    texts = []
    y = []
    
    print("Processing dataset...")
    for item in tqdm(dataset):
        text = item['text']
        labels = item['labels']
        
        # Multi-label strategy: Pick the first label for simplicity
        # (Logistic Regression is multi-class, not multi-label by default)
        if len(labels) > 0:
            texts.append(text)
            y.append(labels[0]) # Integer label
            
    print(f"Training on {len(texts)} samples.")
    
    # Generate Embeddings
    print("Generating embeddings (this may take a moment)...")
    X = []
    batch_size = 32
    
    for i in tqdm(range(0, len(texts), batch_size)):
        batch_texts = texts[i:i+batch_size]
        embeddings, _ = embedder.encode(batch_texts)
        X.extend(embeddings)
        
    X = np.array(X)
    y = np.array(y)
    
    # Train Classifier
    print("Training Logistic Regression...")
    clf = LogisticRegression(max_iter=1000, verbose=1, n_jobs=-1)
    clf.fit(X, y)
    
    # Save Model
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "emotion_classifier.pkl")
    print(f"Saving model to {model_path}...")
    
    joblib.dump({
        "model": clf,
        "labels": LABELS
    }, model_path)
    
    print("Done! Model saved.")
    
    # Test on a few examples
    test_phrases = [
        "I am so happy this works!",
        "This code is garbage and I hate it.",
        "I have no idea what is going on.",
        "That was hilarious lol"
    ]
    
    print("\n--- Test Predictions ---")
    for phrase in test_phrases:
        emb, _ = embedder.encode(phrase)
        # Reshape for single sample
        emb = np.array(emb).reshape(1, -1)
        pred_idx = clf.predict(emb)[0]
        pred_label = LABELS[pred_idx]
        print(f"'{phrase}' -> {pred_label}")

if __name__ == "__main__":
    train()
