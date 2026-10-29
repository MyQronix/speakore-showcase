"""Capability matching: embed a command and a few capability descriptions with Qwen3-Embedding (1024 dims), pick the best."""
import math
import os

from openai import OpenAI

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1/", api_key=os.environ["NEBIUS_API_KEY"])

capabilities = [
    "Send an email to a contact",
    "Show today's calendar events",
    "Switch the app to dark mode",
    "Read the latest unread email",
]
command = "¿Qué tengo en la agenda hoy?"


def embed(texts: list[str]) -> list[list[float]]:
    result = client.embeddings.create(model="Qwen/Qwen3-Embedding-8B", input=texts, dimensions=1024)
    return [item.embedding for item in result.data]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


vectors = embed(capabilities + [command])
query = vectors[-1]
ranked = sorted(zip(capabilities, vectors[:-1]), key=lambda pair: cosine(query, pair[1]), reverse=True)
for text, vector in ranked:
    print(f"{cosine(query, vector):.3f}  {text}")
