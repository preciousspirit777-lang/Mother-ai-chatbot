
import streamlit as st
import sqlite3
from google import genai
from google.genai import types

# =====================================
# MOTHER AI CONFIGURATION
# =====================================

MODEL = "gemini-3.8-flash"
DB_NAME = "mother_ai.db"

st.set_page_config(
    page_title="Mother AI",
    page_icon="🤖"
)

st.title("🤖 Mother AI")
st.caption("Celesta Tech | Intelligent Working System")

# =====================================
# DATABASE
# =====================================

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                role TEXT,
                message TEXT
            )
        """)

def save_message(role, message):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO chat_history VALUES (?, ?)",
            (role, message)
        )

def load_messages(limit=20):
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute(
            """
            SELECT role, message
            FROM chat_history
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return list(reversed(rows))

def clear_history():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM chat_history")

init_db()

# =====================================
# SIDEBAR
# =====================================

with st.sidebar:
    st.header("Settings")

    api_key = st.text_input(
        "Gemini API Key",
        type="password"
    )

    if st.button("Clear Chat History"):
        clear_history()
        st.rerun()

if not api_key:
    st.info("Enter your Gemini API key to begin.")
    st.stop()

# =====================================
# AI CLIENT
# =====================================

retry_options = types.HttpRetryOptions(
    attempts=3,
    initial_delay=2.0,
    max_delay=15.0,
    http_status_codes=[408, 429, 500, 502, 503, 504]
)

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        api_version="v1",
        retry_options=retry_options
    )
)

# =====================================
# SYSTEM INSTRUCTION
# =====================================

SYSTEM_INSTRUCTION = """
You are Mother AI, the central intelligence
assistant of Celesta Tech.

Your responsibilities are:

1. Help users understand concepts.
2. Assist with software engineering.
3. Organize ideas and projects.
4. Maintain context from supplied conversation history.
5. Explain your reasoning clearly.
6. Never invent information when uncertain.

You are a developing AI assistant.
Do not claim capabilities that have not
actually been implemented.
"""

# =====================================
# DISPLAY HISTORY
# =====================================

history = load_messages()

for role, message in history:
    with st.chat_message(role):
        st.markdown(message)

# =====================================
# GENERATE RESPONSE
# =====================================

if prompt := st.chat_input("Talk to Mother AI..."):

    with st.chat_message("user"):
        st.markdown(prompt)

    save_message("user", prompt)

    # Reload history, including current message
    history = load_messages()

    # Convert database history into Gemini format
    conversation = []

    for role, message in history:
        conversation.append({
            "role": "user" if role == "user" else "model",
            "parts": [{"text": message}]
        })

    with st.chat_message("assistant"):

        with st.spinner("Mother AI is thinking..."):

            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=conversation,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        max_output_tokens=1500
                    )
                )

                ai_text = response.text or (
                    "I couldn't generate a text response."
                )

            except Exception as error:

                error_code = getattr(error, "code", None)

                if error_code == 503:
                    ai_text = (
                        "Mother AI is temporarily busy. "
                        "Please try again shortly."
                    )

                elif error_code == 429:
                    ai_text = (
                        "The AI service has reached a usage "
                        "limit. Please try again later."
                    )

                else:
                    ai_text = (
                        "An unexpected error occurred. "
                        "Please check your API configuration "
                        "and try again."
                    )

            st.markdown(ai_text)

    save_message("assistant", ai_text)
