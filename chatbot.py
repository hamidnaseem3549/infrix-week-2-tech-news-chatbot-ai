"""
chatbot.py
----------
RAG (Retrieval-Augmented Generation) chatbot engine.

Flow:
  User query → keyword retrieval → top-K articles → Groq prompt → answer

No vector database required — keyword scoring works well for news Q&A.
"""

import json
import os
import re

from groq import Groq


def _friendly_groq_error(error: Exception) -> str:
    message = str(error)
    lowered = message.lower()
    if "invalid api key" in lowered or "unauthorized" in lowered or "401" in message:
        return (
            "⚠️ Groq API error: your API key is invalid. "
            "Update GROQ_API_KEY in .env with a valid key from Groq Console, "
            "then restart the app."
        )
    if "429" in message or "rate limit" in lowered or "quota" in lowered:
        return (
            "⚠️ Groq API rate limit reached. Please try again later."
        )
    return f"⚠️ Groq API error: {error}"


def _retrieval_fallback(articles: list[dict]) -> str:
    """Return a lightweight answer when Groq cannot be reached."""
    if not articles:
        return (
            "⚠️ Groq is unavailable, and I couldn't find matching articles to fall back on. "
            "Please try a different query."
        )

    lines = [
        "⚠️ Groq is temporarily unavailable, so here are the most relevant articles instead:",
    ]
    for article in articles[:3]:
        lines.append(f"- {article['title']} ({article['date']})")
    lines.append("Please retry after Groq becomes available again.")
    return "\n".join(lines)


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_articles(path: str = "data/articles.json") -> list[dict]:
    """Load scraped articles from disk."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n'{path}' not found.\n"
            "Please run the scraper first:\n\n"
            "    python scraper.py\n"
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        raise ValueError("articles.json is empty. Re-run scraper.py.")
    return data


# ── Retrieval ──────────────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "is", "in", "on", "at", "to", "of", "and", "or",
    "what", "how", "why", "when", "who", "are", "was", "were", "has",
    "have", "had", "do", "does", "did", "for", "with", "about", "tell",
    "me", "i", "my", "can", "you", "please", "from", "this", "that",
}


def retrieve(query: str, articles: list[dict], top_k: int = 5) -> list[dict]:
    """
    Score each article by query-word overlap.
    Title matches count double — titles are the most signal-dense field.
    Falls back to the most recent articles if nothing scores.
    """
    words = set(re.findall(r"\w+", query.lower())) - STOPWORDS
    if not words:
        return articles[:top_k]

    scored = []
    for art in articles:
        title_words = set(re.findall(r"\w+", art["title"].lower()))
        body_words  = set(re.findall(r"\w+", art["content"].lower()))
        score = (
            2 * len(words & title_words) +
            1 * len(words & body_words)
        )
        scored.append((score, art))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [art for score, art in scored if score > 0][:top_k]

    return top if top else articles[:top_k]


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def build_prompt(query: str, articles: list[dict]) -> str:
    """Assemble a grounded prompt for Groq."""
    context = ""
    for i, art in enumerate(articles, 1):
        snippet = art["content"][:700].rstrip()
        context += (
            f"[Article {i}]\n"
            f"Title  : {art['title']}\n"
            f"Date   : {art['date']}\n"
            f"URL    : {art['url']}\n"
            f"Content: {snippet}…\n\n"
        )

    return f"""You are an AI assistant specialised in technology news sourced from BBC Technology.

Rules:
- Answer ONLY using the article context provided below.
- If the answer is not present in the context, say: "I couldn't find relevant information in the scraped articles. Try rephrasing or ask about a different topic."
- Be concise and factual. Mention which article your answer is based on.
- Do not fabricate facts or dates.

===== CONTEXT =====
{context.strip()}
===================

User Question: {query}

Answer:"""


# ── Chatbot Class ──────────────────────────────────────────────────────────────

class DawnChatbot:
    """
    Main chatbot object. Initialise once per session, call .chat() repeatedly.
    """

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
        self.articles = load_articles()
        self.history: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def chat(self, query: str) -> str:
        """Process a user question and return an AI-generated answer."""
        relevant = retrieve(query, self.articles)
        prompt   = build_prompt(query, relevant)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You answer strictly from the provided article context."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            friendly_error = _friendly_groq_error(e)
            if "rate limit" in friendly_error.lower():
                answer = f"{friendly_error}\n\n{_retrieval_fallback(relevant)}"
            else:
                answer = friendly_error

        self.history.append({"role": "user",      "content": query})
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def article_count(self) -> int:
        return len(self.articles)

    def sample_titles(self, n: int = 6) -> list[str]:
        return [a["title"] for a in self.articles[:n]]

    def clear_history(self) -> None:
        self.history = []
