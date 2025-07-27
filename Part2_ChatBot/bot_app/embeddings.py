import json
import numpy as np
import openai
import os
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

VECTORS_FILE = "saved_vectors/vectors.json"

def cosine_similarity(vec1, vec2):
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=[text]
    )
    return response.data[0].embedding

def find_similar_chunks(question, top_k=3):
    question_emb = get_embedding(question)

    with open(VECTORS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    similarities = []
    for item in data:
        score = cosine_similarity(question_emb, item["embedding"])
        similarities.append((score, item["text"]))

    top_chunks = sorted(similarities, key=lambda x: x[0], reverse=True)[:top_k]
    return [text for _, text in top_chunks]
