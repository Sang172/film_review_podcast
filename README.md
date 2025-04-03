# CineCast AI

CineCast AI is a Python application that leverages Large Language Models (LLMs) to generate a comprehensive movie review podcast by summarizing and synthesizing multiple YouTube video reviews.

- Team members: Andrea Quiroz, Nihal Karim, Peeyush Patel, Sang Ahn, Suhho Lee

## Overview

The application takes a movie title as input, searches YouTube for relevant reviews, retrieves the transcripts for the videos, summarizes each review using a Gemini model, combines these summaries into a single comprehensive review, and finally generates an audio podcast of this consolidated review using Google Cloud Text-to-Speech.

## Features

- **YouTube Review Search:** Automatically searches YouTube for movie reviews based on the provided title.
- **Transcript Retrieval:** Fetches the transcripts for relevant YouTube review videos.
- **Individual Review Summarization:** Utilizes the Gemini LLM to generate concise summaries of each identified review.
- **Comprehensive Review Synthesis:** Combines and synthesizes the individual review summaries into a detailed and comprehensive overview of the movie.
- **Podcast Generation:** Converts the final synthesized review into an audio podcast using Google Cloud Text-to-Speech.
- **Streamlit Interface:** Provides a simple and user-friendly web interface to input the movie title and download the generated podcast.