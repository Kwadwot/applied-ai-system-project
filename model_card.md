# Model Card: Number Guessing Game with RAG Game Coach

## 1. Model Name

**GameCoach 1.0**

---

## 2. Intended Use

**GameCoach** is a RAG-powered coaching assistant embedded in a number guessing game. When a player is stuck or wants strategic guidance, it retrieves relevant strategy documents from a curated knowledge base and generates a short, personalized hint using Gemini 2.0 Flash. The system assumes the player wants actionable guidance grounded in number-guessing strategy rather than open-ended conversation, and that the game state (difficulty, guess history, last feedback) is sufficient context to generate a useful hint.

---

## 3. How the Model Works

When the player clicks "Ask the Coach," the current game state — difficulty level, number range, integer guess history, and last feedback outcome (Too High / Too Low / none) — is used to build a natural language retrieval query. That query is embedded using `sentence-transformers` (`all-MiniLM-L6-v2`) and compared against a ChromaDB in-memory collection of 10 pre-embedded strategy documents. The 3 most semantically similar documents are retrieved and concatenated into a context block, which is combined with the live game state into a single prompt sent to Gemini 2.0 Flash. Gemini generates a 2–3 sentence coaching hint grounded in the retrieved strategy text. The ChromaDB collection is built once at startup using `st.cache_resource` and reused for every subsequent query within the session.

---

## 4. Data

The knowledge base contains 10 handwritten strategy documents covering:

- **Binary search** — the optimal midpoint-guessing strategy
- **Too High / Too Low tactics** — how to update bounds after each feedback
- **Opening strategy** — best first guesses per difficulty range
- **Per-difficulty tips** — specific guidance for Easy (1–20), Normal (1–50), and Hard (1–100) modes
- **Low-attempts pressure** — strategy when nearly out of guesses
- **Scoring tips** — how attempt count and feedback type affect the score
- **Pattern recognition** — tracking active range across a full game session

Documents are plain text files in `knowledge_base/`. They are concise (3–6 sentences each) and non-overlapping so that retrieved chunks provide complementary rather than redundant context.

---

## 5. Strengths

The retrieval step ensures hints are grounded in real strategy rather than improvised by the LLM. For example, when the last feedback is "Too High" and attempts are low, the query reliably surfaces `too_high_strategy.txt` and `low_attempts_strategy.txt`, producing accurate and specific guidance. Because the knowledge base is small and purpose-built, retrieval precision is high, and there are no off-topic documents to confuse results. The system also degrades gracefully: if no API key is present, it returns a clear error message rather than crashing, and integer-only history filtering prevents prompt injection from invalid guess inputs.

---

## 6. Limitations and Bias

The knowledge base covers standard binary search strategy, which is mathematically optimal but not always intuitive for casual players. Users who ignore the coach's advice and guess emotionally will receive increasingly irrelevant hints as their history diverges from what binary search would predict. The coach has no memory across game sessions, so each new game starts with no knowledge of past patterns or the player's skill level. The system also has no rate limiting, so in a shared or deployed environment a single user could exhaust API quota by repeatedly clicking "Ask the Coach." Finally, the coach never knows the actual secret number, which means it cannot tell the player exactly how close they are, only how to narrow the range efficiently.

---

## 7. Evaluation

**Automated (game logic):**
- `pytest tests/test_game_logic.py` covers 9 unit tests for `check_guess()`, `parse_guess()`, and edge cases including the original string-comparison bug. The key regression test, `test_guess_9_vs_secret_10`, confirms that numerical comparison is used correctly. Under the old string-based logic this would have returned "Too High" due to lexicographical ordering ("9" > "10").
- All 9 tests pass after the bug fixes applied in Modules 1–3.

**Manual (RAG coach):**
- Coach hints were tested at three game phases: at game start (no history), mid-game after mixed Too High / Too Low feedback, and when one attempt remains.
- Gemini's responses were checked for accuracy (does the hint match the retrieved strategy?) and safety (does it avoid revealing or guessing the secret number?).
- No automated evaluation of hint quality is currently implemented; grounding is verified by inspection of the retrieved documents relative to the generated text.

---

## 8. Future Work

- **Expand the knowledge base** with documents on psychological pressure, common mistake patterns, and difficulty-specific worked examples.
- **Add session memory** so the coach can reference the player's performance across multiple games and adapt its advice to their skill level.
- **Automated hint evaluation** using a second LLM call to score each generated hint against the retrieved documents for factual grounding.
- **Rate limiting** on the "Ask the Coach" button to prevent API quota exhaustion in shared or deployed contexts.
- **Persistent ChromaDB store** so the collection does not need to be re-embedded on each cold start once the knowledge base grows large enough to make startup time noticeable.

---

## 9. Personal Reflection

Working on both the original debugging project and the RAG extension taught me two distinct lessons about AI. In Modules 1–3, the main insight was that AI-generated code requires critical evaluation — Copilot correctly identified the string-to-integer comparison bug in `check_guess`, but incorrectly suggested changing the Normal difficulty range to 1–20 instead of 1–50, which I had to catch and correct myself. Documenting those AI contributions in commit messages forced a level of accountability that changed how I review AI suggestions.

Adding the RAG system in the final project shifted my perspective from debugging AI output to designing AI pipelines. Connecting three components — an embedding model, a vector store, and a generation model — meant each had to be understood independently before the integration made sense. The most surprising realization was how much the quality of retrieval depends on the quality of the knowledge base documents: vague or overlapping documents produce vague hints, regardless of how capable the generation model is. Separating logic from the main program (a habit developed in Modules 1–3) made the RAG module straightforward to test and replace independently. In future projects, I want to apply the same separation-of-concerns principle to AI pipeline components from the start rather than retrofitting it later.

One practical limitation encountered during development was hitting the Gemini API free-tier quota limit, which prevented live end-to-end testing of the full RAG pipeline. As a result, the coach's generated hints could not be verified against real game sessions, and the Sample Interactions section of the README remains incomplete. This was a useful reminder that API rate limits and quota constraints are real infrastructure concerns and that future projects should account for them early, either by budgeting for paid access or by building a mock generation layer for offline testing.
