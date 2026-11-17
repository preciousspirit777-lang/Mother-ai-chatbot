
import streamlit as st
import sqlite3
import uuid
import time
from contextlib import closing

from google import genai
from google.genai import types


# =====================================================
# 1. CONFIGURATION
# =====================================================

APP_NAME = "Mother AI"
MODEL = "gemini-3.8-flash"

DB_PATH = "mother_ai.db"

MAX_HISTORY_MESSAGES = 16
MAX_OUTPUT_TOKENS = 1200


st.set_page_config(
    page_title="Mother AI | Celesta Tech",
    page_icon="🦅",
    layout="centered"
)


# =====================================================
# 2. INTERFACE DESIGN
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #0B1220;
}

.block-container {
    max-width: 900px;
    padding-top: 2rem;
}

h1 {
    color: #60A5FA;
}

[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 12px;
}

[data-testid="stSidebar"] {
    background-color: #111827;
}

</style>
""", unsafe_allow_html=True)


st.title("🦅 Mother AI")

st.caption(
    "CELESTA TECH | Intelligent Working System"
)

st.markdown(
    "Your intelligent assistant for learning, "
    "engineering, research and project development."
)

st.divider()


# =====================================================
# 3. SESSION MANAGEMENT
# =====================================================

if "mother_ai_session_id" not in st.session_state:

    st.session_state["mother_ai_session_id"] = (
        uuid.uuid4().hex
    )

SESSION_ID = st.session_state["mother_ai_session_id"]


# =====================================================
# 4. DATABASE ENGINE
# =====================================================

def init_db():

    with closing(
        sqlite3.connect(DB_PATH, timeout=30)
    ) as conn:

        with conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    role TEXT NOT NULL,

                    message TEXT NOT NULL,

                    session_id TEXT NOT NULL DEFAULT 'legacy',

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP

                )
            """)

            # Migrate the original two-column database.

            columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(chat_history)"
                ).fetchall()
            }

            if "session_id" not in columns:

                conn.execute("""
                    ALTER TABLE chat_history
                    ADD COLUMN session_id TEXT
                    NOT NULL DEFAULT 'legacy'
                """)

            if "created_at" not in columns:

                conn.execute("""
                    ALTER TABLE chat_history
                    ADD COLUMN created_at TEXT
                """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_chat_session
                ON chat_history(session_id)
            """)


def load_messages(session_id, limit=MAX_HISTORY_MESSAGES):

    with closing(
        sqlite3.connect(DB_PATH, timeout=30)
    ) as conn:

        rows = conn.execute("""
            SELECT role, message

            FROM chat_history

            WHERE session_id = ?

            ORDER BY rowid DESC

            LIMIT ?

        """, (session_id, limit)).fetchall()

    return list(reversed(rows))


def save_exchange(session_id, user_message, ai_message):

    # Save both messages together only after
    # Gemini successfully generates a response.

    with closing(
        sqlite3.connect(DB_PATH, timeout=30)
    ) as conn:

        with conn:

            conn.executemany("""
                INSERT INTO chat_history
                (session_id, role, message)

                VALUES (?, ?, ?)

            """, [
                (session_id, "user", user_message),
                (session_id, "assistant", ai_message)
            ])


def clear_current_chat(session_id):

    with closing(
        sqlite3.connect(DB_PATH, timeout=30)
    ) as conn:

        with conn:

            conn.execute("""
                DELETE FROM chat_history
                WHERE session_id = ?
            """, (session_id,))


# Initialize database

init_db()


# =====================================================
# 5. API KEY MANAGEMENT
# =====================================================

def get_server_api_key():

    try:

        return str(
            st.secrets.get("GEMINI_API_KEY", "")
        ).strip()

    except Exception:

        return ""


SERVER_API_KEY = get_server_api_key()


# =====================================================
# 6. SIDEBAR SETTINGS
# =====================================================

with st.sidebar:

    st.title("⚙️ Settings")

    st.caption("Mother AI Control Panel")

    if SERVER_API_KEY:

        api_key = SERVER_API_KEY

        st.success(
            "API key loaded from Streamlit Secrets."
        )

    else:

        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            key="mother_ai_api_key"
        )

    st.divider()

    st.markdown("### AI Configuration")

    st.write(f"**Model:** {MODEL}")

    st.write("**Provider:** Google Gemini")

    st.write("**Memory:** Recent conversation context")

    st.divider()

    st.markdown("### Conversation")

    if st.button("🗑️ Clear Current Chat"):

        clear_current_chat(SESSION_ID)

        st.rerun()

    st.divider()

    st.caption(
        "Mother AI v0.3 | Celesta Tech"
    )

    st.caption(
        "Prototype database: SQLite. "
        "Production storage requires a durable database."
    )


# =====================================================
# 7. MOTHER AI IDENTITY
# =====================================================

SYSTEM_INSTRUCTION = """

You are Mother AI.

You are the central AI assistant being developed
within the Celesta Tech ecosystem.

YOUR RESPONSIBILITIES:

1. Help users understand difficult concepts.

2. Assist with software engineering and Python.

3. Support research and data analysis.

4. Help organize projects and ideas.

5. Explain technical concepts in simple language.

6. Maintain conversational context using the
   conversation history supplied with each request.

7. Identify assumptions and uncertainty.

8. Give practical, structured and useful answers.

ENGINEERING BEHAVIOUR:

- Be accurate and honest.
- Do not invent facts.
- Do not claim tools or capabilities you do not have.
- Use previous conversation context when relevant.
- If information is missing, ask for clarification.
- Explain important technical decisions.
- Prefer clear solutions over unnecessary complexity.

You are a developing AI assistant.
Never claim to have permanent memory beyond
the information actually supplied to you.

"""


# =====================================================
# 8. CONVERSATION DISPLAY
# =====================================================

history = load_messages(SESSION_ID)

for role, message in history:

    with st.chat_message(role):

        st.markdown(message)


# =====================================================
# 9. API CONNECTION
# =====================================================

if not api_key:

    st.info(
        "Enter your Gemini API key in Settings "
        "to activate Mother AI."
    )

    st.stop()


# =====================================================
# 10. BUILD GEMINI CONVERSATION
# =====================================================

def build_conversation(history, current_prompt):

    conversation = []

    for role, message in history:

        gemini_role = (
            "user" if role == "user" else "model"
        )

        conversation.append(
            types.Content(
                role=gemini_role,
                parts=[
                    types.Part.from_text(
                        text=message
                    )
                ]
            )
        )

    # Add current message.

    conversation.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=current_prompt
                )
            ]
        )
    )

    return conversation


# =====================================================
# 11. GENERATE AI RESPONSE
# =====================================================

def generate_response(prompt, previous_history):

    conversation = build_conversation(
        previous_history,
        prompt
    )

    retry_options = types.HttpRetryOptions(

        attempts=2,

        initial_delay=1.0,

        max_delay=4.0,

        http_status_codes=[
            408,
            500,
            502,
            503,
            504
        ]
    )

    http_options = types.HttpOptions(

        api_version="v1",

        timeout=45000,

        retry_options=retry_options
    )

    generation_config = types.GenerateContentConfig(

        system_instruction=SYSTEM_INSTRUCTION,

        max_output_tokens=MAX_OUTPUT_TOKENS,

        thinking_config=types.ThinkingConfig(
            thinking_level="low"
        )

    )

    response_parts = []

    start_time = time.perf_counter()

    print(
        "MOTHER AI: Request started",
        flush=True
    )

    with genai.Client(

        api_key=api_key,

        http_options=http_options

    ) as client:

        # Stream response instead of waiting
        # for the entire answer to finish.

        stream = client.models.generate_content_stream(

            model=MODEL,

            contents=conversation,

            config=generation_config

        )

        for chunk in stream:

            text_piece = chunk.text

            if text_piece:

                response_parts.append(text_piece)

                yield_text = "".join(response_parts)

                yield yield_text

    final_response = "".join(response_parts).strip()

    if not final_response:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    elapsed = time.perf_counter() - start_time

    print(
        f"MOTHER AI: Response completed in "
        f"{elapsed:.2f} seconds",
        flush=True
    )


# =====================================================
# 12. CHAT INPUT
# =====================================================

prompt = st.chat_input(
    "Talk to Mother AI..."
)


if prompt:

    with st.chat_message("user"):

        st.markdown(prompt)

    with st.chat_message("assistant"):

        status = st.status(
            "Connecting to Mother AI...",
            expanded=False
        )

        response_placeholder = st.empty()

        full_response = ""

        try:

            status.update(
                label="Mother AI is processing...",
                state="running"
            )

            # Stream incoming text.

            for partial_response in generate_response(
                prompt,
                history[-MAX_HISTORY_MESSAGES:]
            ):

                full_response = partial_response

                response_placeholder.markdown(
                    full_response + "▌"
                )

            response_placeholder.markdown(
                full_response
            )

            status.update(
                label="Response completed successfully.",
                state="complete"
            )

            # Save only successful exchanges.

            save_exchange(
                SESSION_ID,
                prompt,
                full_response
            )

            st.caption(
                f"Model: {MODEL} | Response generated."
            )

        except Exception as error:

            error_code = getattr(
                error,
                "code",
                None
            )

            print(
                f"MOTHER AI ERROR: "
                f"{type(error).__name__}: {error}",
                flush=True
            )

            status.update(
                label="Mother AI could not complete the request.",
                state="error"
            )

            if error_code == 503:

                st.error(
                    "Gemini is temporarily overloaded. "
                    "Please try again shortly."
                )

            elif error_code == 429:

                st.error(
                    "The Gemini API usage limit has "
                    "been reached. Check your quota."
                )

            elif error_code in (401, 403):

                st.error(
                    "API authentication failed. "
                    "Check your Gemini API key."
                )

            elif error_code == 404:

                st.error(
                    "The requested model or API resource "
                    "could not be found."
                )

            elif error_code == 400:

                st.error(
                    "Gemini rejected the request. "
                    "Check the model and generation settings."
                )

            else:

                st.error(
                    "An unexpected error interrupted "
                    "the request. Check the application logs."
                )

            with st.expander("Technical diagnostic"):

                st.write(
                    f"Error type: {type(error).__name__}"
                )

                st.write(
                    f"HTTP/API code: {error_code}"
                )

                st.caption(
                    "The failed exchange was not saved "
                    "as a successful conversation."
                )
