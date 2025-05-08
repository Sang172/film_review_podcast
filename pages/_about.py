import streamlit as st

st.set_page_config(page_title="About CineCast AI", page_icon="📄")

st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #1c1c1c;
        color: #f5f5f5;
        font-family: 'Courier New', monospace;
    }

    .centered-container {
        max-width: 620px;
        margin-left: auto;
        margin-right: auto;
    }

    div.stForm {
        background-color: #2e2e2e;
        border: 2px dashed #888;
        border-radius: 0;
        padding: 24px;
    }

    div.stForm input, div.stForm .stTextInput>div>input {
        background-color: #000 !important;
        color: #fff !important;
        border: 2px solid #fff;
    }

    div.stForm .stCheckbox>label {
        color: #ccc !important;
        font-weight: bold;
    }

    div.stForm button[kind="primary"] {
        background-color: #000 !important;
        color: #fff !important;
        border: 2px solid #fff !important;
        font-weight: bold !important;
        text-transform: uppercase;
    }

    .movie-card {
        border: 2px dashed #888;
        border-radius: 0px;
        padding: 20px;
        margin: 30px auto;
        display: flex;
        gap: 25px;
        align-items: flex-start;
        background: #2e2e2e;
        font-family: 'Courier New', monospace;
        width: 620px;
        max-width: 100%;
    }

    .poster-container {
        flex-shrink: 0;
        border: 2px solid #aaa;
    }

    .movie-poster {
        width: 200px;
        height: auto;
        display: block;
    }

    .movie-info h1, .movie-info h3, .movie-summary {
        color: #f5f5f5;
    }

    [data-testid="stSidebar"] {
        background-color: #2e2e2e;
        border-right: 3px solid #888;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📄 About CineCast AI")

st.subheader("'Where Reviews Go from Screen to Stream'")

st.markdown("""
CineCast AI is an AI-powered application that generates podcast-style movie discussions 
based on YouTube reviews. The platform combines the power of Large Language Models and speech synthesis.

### 💡 Features
- Summarizes YouTube movie reviews
- Generates AI-narrated podcast audio
- Offers spoiler-free or deep-dive options
- Stores your podcasts and metadata in GCS

### 🛠️ Technologies
- Streamlit UI hosted on GCP Cloud Run
- YouTube API + Gemini + Google Text-to-Speech
- CI/CD via GitHub Actions
            
### 📐 The Team
- A combination of cinephiles and data nerds, we are graduate students at the University of San Francisco!
            Built by Andrea Quiroz, Nihal Karim, Peeyush Patel, Sang Ahn, and Suhho Lee

---
""")