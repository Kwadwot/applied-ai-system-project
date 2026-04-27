import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import google.generativeai as genai

KB_PATH = Path(__file__).parent / "knowledge_base"


def load_collection():
    """
    Embed all knowledge base docs into an in-memory ChromaDB collection.
    Called once at startup via st.cache_resource — no server required.
    """
    ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.EphemeralClient()
    collection = client.create_collection("game_coach", embedding_function=ef)

    docs, ids = [], []
    for i, path in enumerate(sorted(KB_PATH.glob("*.txt"))):
        docs.append(path.read_text(encoding="utf-8").strip())
        ids.append(f"doc_{i}")

    if docs:
        collection.add(documents=docs, ids=ids)

    return collection


def _build_query(game_state: dict) -> str:
    parts = []
    last = game_state.get("last_outcome", "")
    if last == "Too High":
        parts.append("guessed too high need to go lower reduce upper bound")
    elif last == "Too Low":
        parts.append("guessed too low need to go higher raise lower bound")
    else:
        parts.append("starting the game best first guess opening strategy")

    parts.append(
        f"{game_state['difficulty']} difficulty "
        f"range {game_state['low']} to {game_state['high']}"
    )

    if game_state.get("attempts_remaining", 10) <= 2:
        parts.append("running out of attempts critical pressure")

    return " ".join(parts)


def get_coach_hint(game_state: dict, collection) -> str:
    """Retrieve relevant strategy docs and generate a personalised hint via Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "No GEMINI_API_KEY found. "
            "Set it as an environment variable to enable the Game Coach."
        )

    query = _build_query(game_state)
    results = collection.query(query_texts=[query], n_results=3)
    context = "\n\n---\n\n".join(results["documents"][0])

    prompt = (
        "You are a friendly game coach for a number guessing game.\n\n"
        f"Strategy knowledge base:\n{context}\n\n"
        "Current game state:\n"
        f"- Difficulty: {game_state['difficulty']} "
        f"(range {game_state['low']}–{game_state['high']})\n"
        f"- Guesses so far: {game_state.get('history', [])}\n"
        f"- Last feedback: {game_state.get('last_outcome', 'None yet')}\n"
        f"- Attempts remaining: {game_state['attempts_remaining']}\n\n"
        "Give a short (2–3 sentences), encouraging strategy hint based on "
        "the knowledge base and the player's current situation. "
        "Never reveal or guess the secret number."
    )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text
