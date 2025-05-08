# pages/1_🎙️_Podcasts.py
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Podcasts Library", page_icon="🎙️")

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

st.title("🎙️ Podcasts Library")
st.markdown(
    """
    Browse and filter your CineCast AI episodes.
    This is a prototype—clicking “Play” won’t actually play audio yet!
    """
)

# ─── Dummy Episode Data ───
# In your real app this could come from GCS or a database.
placeholder_url = Path("static/image.png").as_posix()

episodes = [
    {
        "title": "Inception Deep Dive",
        "genre": "Sci-Fi",
        "year": 2010,
        "length": "12 min",
        "spoiler_free": False,
        "poster": placeholder_url
    },
    {
        "title": "The Godfather Breakdown",
        "genre": "Crime",
        "year": 1972,
        "length": "7 min",
        "spoiler_free": True,
        "poster": placeholder_url
    },
    {
        "title": "Pride & Prejudice Review",
        "genre": "Romance",
        "year": 2005,
        "length": "3 min",
        "spoiler_free": True,
        "poster": placeholder_url
    },
    {
        "title": "Jurassic Park Analysis",
        "genre": "Adventure",
        "year": 1993,
        "length": "12 min",
        "spoiler_free": False,
        "poster": placeholder_url
    },
    {
        "title": "The Matrix Discussion",
        "genre": "Sci-Fi",
        "year": 1999,
        "length": "7 min",
        "spoiler_free": True,
        "poster": placeholder_url
    },
]

df = pd.DataFrame(episodes)

# ─── Filter Bar ───
with st.sidebar:
    st.header("Filters")
    genres = sorted(df["genre"].unique())
    years = sorted(df["year"].unique())
    chosen_genres = st.multiselect("Genre", genres, default=genres)
    chosen_years = st.slider("Decade", min(years), max(years), (min(years), max(years)), step=10)

# apply filters
filtered = df[
    df["genre"].isin(chosen_genres) &
    df["year"].between(chosen_years[0], chosen_years[1])
]

st.markdown(f"**{len(filtered)} episodes found**")

# ─── Episode Grid ───
cols = st.columns(3, gap="medium")
for idx, ep in filtered.iterrows():
    col = cols[idx % 3]
    with col:
        st.image(ep["poster"], use_container_width=True)
        st.markdown(f"### {ep['title']}")
        st.markdown(f"**{ep['genre']}** • {ep['year']} • {ep['length']}")
        st.markdown(
            "✅ Spoiler-Free" if ep["spoiler_free"] else "🚨 Includes Spoilers"
        )
        st.button("▶️ Play", key=f"play_{idx}")

# ─── End of Prototype ───