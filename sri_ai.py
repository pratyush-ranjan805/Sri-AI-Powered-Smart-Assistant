import streamlit as st
from groq import Groq
import time
from PyPDF2 import PdfReader
import sqlite3

# ------------------ DATABASE ------------------
conn = sqlite3.connect("sri_app.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    username TEXT,
    role TEXT,
    content TEXT
)
""")

conn.commit()

# ------------------ SESSION ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------ LOGIN ------------------
if not st.session_state.logged_in:
    st.title("🔐 Sri AI Login")

    menu = ["Login", "Signup"]
    choice = st.selectbox("Select Option", menu)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if choice == "Signup":
        if st.button("Create Account"):
            cursor.execute("INSERT INTO users VALUES (?, ?)", (username, password))
            conn.commit()
            st.success("Account created! Please login.")

    if choice == "Login":
        if st.button("Login"):
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            data = cursor.fetchone()

            if data:
                st.session_state.logged_in = True
                st.session_state.username = username

                cursor.execute("SELECT role, content FROM chats WHERE username=?", (username,))
                data = cursor.fetchall()
                st.session_state.messages = [{"role": r, "content": c} for r, c in data]

                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.stop()

# ------------------ CONFIG ------------------
if "GROQ_API_KEY" not in st.secrets:
    st.error("API key missing. Please add in Streamlit Secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(
    page_title="Sri AI",
    page_icon="🤖",
    layout="wide"
)

# ------------------ SAME UI ------------------
st.markdown("""
<style>
.stApp {background-color: #0E1117; color: white;}
[data-testid="stChatMessage"] {border-radius: 12px; padding: 10px; margin-bottom: 10px;}
[data-testid="stChatMessage"][aria-label="user"] {background-color: #1E1E1E;}
[data-testid="stChatMessage"][aria-label="assistant"] {background-color: #262730;}
.stChatInput input {background-color: #1E1E1E !important; color: white !important; border-radius: 10px;}
section[data-testid="stSidebar"] {background-color: #111827;}
.stButton button {background-color: #2563EB; color: white; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

# ------------------ PDF ------------------
def read_pdf(file):
    pdf = PdfReader(file)
    text = ""
    for page in pdf.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

# ------------------ SIDEBAR ------------------
with st.sidebar:
    st.title("🤖 Sri AI")

    st.write(f"👤 {st.session_state.username}")

    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.messages = []
        st.rerun()

    st.markdown("### 🚀 Features")
    st.write("✔ Smart AI Chat")
    st.write("✔ PDF Chat")
    st.write("✔ Memory")
    st.write("✔ Login System")

    st.markdown("---")

    uploaded_file = st.file_uploader("📄 Upload PDF", type="pdf")

    if st.button("🗑 Clear Chat"):
        st.session_state.messages = []
        cursor.execute("DELETE FROM chats WHERE username=?", (st.session_state.username,))
        conn.commit()

# ------------------ HEADER ------------------
st.markdown("<h1 style='text-align: center;'>🤖 Sri - AI Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Your smart study & coding partner</p>", unsafe_allow_html=True)

# ------------------ LOAD PDF ------------------
pdf_text = ""
if uploaded_file:
    pdf_text = read_pdf(uploaded_file)

# ------------------ CHAT ------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask Sri anything...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    cursor.execute("INSERT INTO chats VALUES (?, ?, ?)",
                   (st.session_state.username, "user", user_input))
    conn.commit()

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Sri is thinking... 🤔"):
            try:
                final_prompt = user_input

                if pdf_text:
                    final_prompt = f"""
Use this document:

{pdf_text[:1500]}

Question: {user_input}
"""

                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are Sri, a helpful AI assistant."},
                        {"role": "user", "content": final_prompt}
                    ]
                )

                reply = response.choices[0].message.content

            except Exception as e:
                reply = f"⚠️ Error: {str(e)}"

            placeholder = st.empty()
            full_text = ""

            for char in reply:
                full_text += char
                placeholder.markdown(full_text)
                time.sleep(0.002)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    cursor.execute("INSERT INTO chats VALUES (?, ?, ?)",
                   (st.session_state.username, "assistant", reply))
    conn.commit()
