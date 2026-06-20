"""
app.py
------
Streamlit frontend for the Tech News Chatbot.

Run:
    python -m streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv
from chatbot import DawnChatbot

load_dotenv()  # picks up GROQ_API_KEY from .env if present


def looks_like_placeholder_key(value: str) -> bool:
    """Return True when the configured API key is obviously a template value."""
    lowered = value.strip().lower()
    if not lowered:
        return True

    placeholder_markers = (
        "your_",
        "your valid",
        "your_valid",
        "replace_me",
        "replace-with",
        "placeholder",
        "example",
        "changeme",
    )
    if any(marker in lowered for marker in placeholder_markers):
        return True

    return len(lowered) < 20

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tech News Chatbot",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #0b0f19; }

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, #b91c1c 0%, #7f1d1d 100%);
    border-radius: 14px;
    padding: 28px 32px 22px;
    margin-bottom: 28px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(185,28,28,0.3);
}
.app-header h1 { color: #fff; font-size: 1.75rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
.app-header p  { color: #fca5a5; font-size: 0.88rem; margin: 6px 0 0; }

/* ── Stats bar ── */
.stats-bar {
    display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
}
.stat-chip {
    background: #131929;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 0.82rem;
    color: #93c5fd;
    font-weight: 500;
}

/* ── Chat bubbles ── */
.user-bubble {
    background: #1e3a5f;
    border-radius: 14px 14px 3px 14px;
    padding: 12px 18px;
    margin: 10px 0 10px 60px;
    color: #dbeafe;
    font-size: 0.92rem;
    line-height: 1.55;
}
.bot-bubble {
    background: #111827;
    border-left: 3px solid #b91c1c;
    border-radius: 3px 14px 14px 14px;
    padding: 14px 18px;
    margin: 10px 60px 10px 0;
    color: #e5e7eb;
    font-size: 0.92rem;
    line-height: 1.65;
}
.bubble-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.user-bubble .bubble-label { color: #60a5fa; }
.bot-bubble  .bubble-label { color: #f87171; }

/* ── Welcome card ── */
.welcome-card {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 20px;
    color: #d1d5db;
    font-size: 0.9rem;
    line-height: 1.7;
}

/* ── Suggestion buttons ── */
.stButton > button {
    background: #131929 !important;
    border: 1px solid #1e3a5f !important;
    color: #93c5fd !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    padding: 8px 12px !important;
    text-align: left !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: #1e3a5f !important;
    border-color: #3b82f6 !important;
    color: #dbeafe !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1520 !important;
    border-right: 1px solid #1e2d40 !important;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── Input ── */
.stChatInput textarea {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    color: #f1f5f9 !important;
    border-radius: 10px !important;
}

/* ── Divider ── */
hr { border-color: #1e2d40 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Setup")

    # API key: env var takes priority, then sidebar input
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        if looks_like_placeholder_key(env_key):
            api_key = ""
            st.error(
                "⚠️ GROQ_API_KEY looks like a placeholder. Replace it in .env with a real key from Groq."
            )
        else:
            api_key = env_key
            st.success("✅ API key loaded from environment")
    else:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_…",
            help="Key from console.groq.com",
        ).strip()

    st.markdown("---")
    st.markdown("## 📖 How It Works")
    st.markdown("""
**RAG Architecture:**

1. 🕷️ **Scrape** — BeautifulSoup collects Dawn.com tech articles
2. 🔍 **Retrieve** — keyword scoring finds relevant articles for your query
3. 🤖 **Generate** — Groq reads those articles and answers accurately

This is the same architecture used in enterprise AI assistants.
    """)

    st.markdown("---")
    st.markdown("## 🔗 Links")
    st.markdown("""
- [Dawn Tech News](https://dawn.com/tech)
- [Groq Console](https://console.groq.com)
- [Project on GitHub](https://github.com/hamidnaseem47/dawn-tech-chatbot)
    """)

    st.markdown("---")
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        if "bot" in st.session_state:
            st.session_state.bot.clear_history()
        st.rerun()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>📰 Tech News Chatbot</h1>
    <p>RAG-powered AI assistant · Sourced from BBC Technology · Built with Groq</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bot" not in st.session_state:
    st.session_state.bot = None

# ── Initialise chatbot ─────────────────────────────────────────────────────────
if api_key and st.session_state.bot is None:
    try:
        with st.spinner("Loading articles and connecting to Groq…"):
            st.session_state.bot = DawnChatbot(api_key=api_key)
        count = st.session_state.bot.article_count()
        st.markdown(f"""
        <div class="stats-bar">
            <div class="stat-chip">📄 {count} articles loaded</div>
            <div class="stat-chip">🤖 Groq llama-3.1-8b-instant</div>
            <div class="stat-chip">🔍 RAG retrieval active</div>
        </div>
        """, unsafe_allow_html=True)
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Failed to start chatbot: {e}")
        st.stop()
elif not api_key:
    st.warning("👈 Enter your Groq API key in the sidebar to begin.")

# ── Welcome card + suggestions (shown on fresh start) ─────────────────────────
if not st.session_state.messages and st.session_state.bot:
    st.markdown("""
    <div class="welcome-card">
        👋 <strong>Welcome!</strong> I'm trained on recent technology news from the scraped articles.<br><br>
        Ask me about AI trends, robotics, cybersecurity, gadgets, mobile networks,
        data centres, gaming, deepfakes, or other topics covered in the articles.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**💡 Try one of these:**")
    suggestions = [
        "What does the article say about GTA 6?",
        "What are the concerns about delivery robots?",
        "What does the article say about children and the social media ban?",
        "What are the main points about AI data centres?",
        "Why are police warning about deepfakes?",
        "What does the article say about driverless cars in London?",
    ]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"s{i}"):
            st.session_state["_pending"] = s
            st.rerun()

# ── Render chat history ────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">'
            f'<div class="bubble-label">You</div>{msg["content"]}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="bot-bubble">'
            f'<div class="bubble-label">🤖 Tech AI</div>{msg["content"]}'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Handle input ───────────────────────────────────────────────────────────────
query = st.chat_input("Ask about Tech news…")

# suggestion chip click
if "_pending" in st.session_state:
    query = st.session_state.pop("_pending")

if query:
    if not st.session_state.bot:
        st.warning("⚠️ Please enter your Groq API key in the sidebar first.")
    else:
        # Show user message immediately
        st.markdown(
            f'<div class="user-bubble">'
            f'<div class="bubble-label">You</div>{query}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "user", "content": query})

        # Generate answer
        with st.spinner("Searching articles and generating answer…"):
            answer = st.session_state.bot.chat(query)

        st.markdown(
            f'<div class="bot-bubble">'
            f'<div class="bubble-label">🤖 Tech AI</div>{answer}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
