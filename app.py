import streamlit as st
import sqlite3
from google import genai

st.title("🤖 Mother AI: Database Chatbot")
st.write("Your conversations are permanently saved.")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('mother_ai.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (role TEXT, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

def save_message(role, message):
    conn = sqlite3.connect('mother_ai.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (role, message) VALUES (?, ?)", (role, message))
    conn.commit()
    conn.close()

def load_messages():
    conn = sqlite3.connect('mother_ai.db')
    c = conn.cursor()
    c.execute("SELECT role, message FROM chat_history")
    rows = c.fetchall()
    conn.close()
    return rows

# --- UI SETUP ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key:", type="password")
    
    if st.button("Clear Chat History"):
        conn = sqlite3.connect('mother_ai.db')
        c = conn.cursor()
        c.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()
        st.rerun()

if not api_key:
    st.info("👈 Enter your API key in the sidebar to start chatting.")
    st.stop()

# Initialize the AI client
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Failed to connect: {e}")
    st.stop()

# Load previous messages from the database
history = load_messages()
for role, msg in history:
    with st.chat_message(role):
        st.markdown(msg)

# Chat input
if prompt := st.chat_input("Ask Mother AI anything..."):
    # 1. Display and save user message
    st.chat_message("user").markdown(prompt)
    save_message("user", prompt)

    # 2. Generate and save AI response
    with st.spinner("Mother AI is thinking..."):
        try:
            response = client.models.generate_content(
                model="models/gemini-2.5-flash", # Using a stable model name
                contents=prompt,
            )
            ai_text = response.text
        except Exception as e:
            ai_text = f"❌ Error: {e}"

    with st.chat_message("assistant"):
        st.markdown(ai_text)
    save_message("assistant", ai_text)
