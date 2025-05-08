# CineCast AI

CineCast AI is a Python application that leverages Large Language Models (LLMs) to generate a comprehensive movie review podcast by summarizing and synthesizing multiple YouTube video reviews.

Team members: Andrea Quiroz, Nihal Karim, Peeyush Patel, Sang Ahn, Suhho Lee

---

## Overview

The application takes a movie title as input, searches YouTube for relevant reviews, retrieves the transcripts for the videos, summarizes each review using a Gemini model, combines these summaries into a single comprehensive review, and finally generates an audio podcast of this consolidated review using Google Cloud Text-to-Speech.

---

## 🌐 Streamlit Dashboard

👉 **[Launch the app](https://film-review-podcast-345058179408.us-west1.run.app)**: Create your own movie podcast!

---

## Features

-   **YouTube Review Search:** Automatically searches YouTube for movie reviews based on the provided title.
-   **Transcript Retrieval:** Fetches the transcripts for relevant YouTube review videos.
-   **Individual Review Summarization:** Utilizes the Gemini LLM to generate concise summaries of each identified review.
-   **Comprehensive Review Synthesis:** Combines and synthesizes the individual review summaries into a detailed and comprehensive overview of the movie.
-   **Spoiler Control:** Choose between spoiler and spoiler-free reviews with a simple toggle:
    *   **Spoiler-Free Mode:** Specifically searches for non-spoiler reviews and filters out content that may reveal major plot points. Filters videos based on title keywords and uses LLM prompt engineering to exclude plot revelations during summarization.
    *   **Spoiler Mode:** Includes detailed plot discussions and major revelations for those who have seen the movie or don't mind spoilers.
-   **Customizable Podcast Length:** Select your preferred podcast duration to tailor the listening experience:
    *   **Clip (~3 min):** A quick glimpse — perfect for when you're short on time.
    *   **Reel (~7 min):** A fast-paced review you can enjoy with your coffee.
    *   **Feature (~12 min):** The default, full movie experience — detailed, thoughtful, and complete.
-   **Podcast Generation:** Converts the final synthesized review into an audio podcast using Google Cloud Text-to-Speech.
-   **Caching:** Utilizes Google Cloud Storage to cache generated reviews and podcasts, significantly speeding up requests for previously processed movies, spoiler preferences, and lengths.
-   **Streamlit Interface:** Provides a simple and user-friendly web interface to input the movie title, select preferences, and download the generated podcast.
