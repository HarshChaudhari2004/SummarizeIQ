import os
import re
import time
import requests
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai
from textblob import TextBlob
import nltk

nltk.download('punkt')

# Load API keys from .env file
load_dotenv()
YOUTUBE_API_KEY = "AIzaSyCnsaGgPy9QivVVKsxsfZ4_qE3OTz3DfXg"
GEMINI_API_KEY = "AIzaSyAs3_dAYF7KMlWJrpdyC9TbXMwsu73A_bg"

def extract_video_id(url):
    """Extracts the video ID from a YouTube URL."""
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

def fetch_comments(video_id, max_comments=1777):
    """Fetches comments from a YouTube video using the YouTube Data API v3."""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    comments = []
    next_page_token = None

    st.info("Fetching comments...")
    with st.spinner("Fetching comments..."):
        try:
            with tqdm(total=max_comments, desc="Fetching comments") as pbar:
                while len(comments) < max_comments:
                    request = youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=100,  # Maximum number of comments per request
                        textFormat='plainText',
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    for item in response['items']:
                        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                        comments.append(comment)
                        pbar.update(1)
                        if len(comments) >= max_comments:
                            break
                    next_page_token = response.get('nextPageToken')
                    if not next_page_token or len(comments) >= max_comments:
                        break
        except HttpError as e:
            if e.resp.status == 403:
                st.error("Comments are disabled for this video.")
            else:
                st.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
            return []
    return comments

def fetch_live_chat(video_id, max_messages=777):
    """Fetches live chat messages from a YouTube live stream using the YouTube Data API v3."""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    live_chat_messages = []
    next_page_token = None
    retry_count = 0
    max_retries = 5
    retry_delay = 5  # 5 seconds delay between retries

    try:
        video_response = youtube.videos().list(part='liveStreamingDetails', id=video_id).execute()
        if 'liveStreamingDetails' not in video_response['items'][0]:
            st.error("Live chat not found for this video.")
            return live_chat_messages
        live_chat_id = video_response['items'][0]['liveStreamingDetails'].get('activeLiveChatId')

        if not live_chat_id:
            st.error("Live chat not found for this video.")
            return live_chat_messages

        st.info("Fetching live chat messages...")
        with st.spinner("Fetching live chat messages..."):
            with tqdm(total=max_messages, desc="Fetching live chat") as pbar:
                while len(live_chat_messages) < max_messages:
                    try:
                        request = youtube.liveChatMessages().list(
                            liveChatId=live_chat_id,
                            part='snippet',
                            maxResults=200,  # Maximum number of messages per request
                            pageToken=next_page_token
                        )
                        response = request.execute()
                        for item in response['items']:
                            if 'textMessageDetails' in item['snippet']:
                                live_chat_message = item['snippet']['textMessageDetails']['messageText']
                                live_chat_messages.append(live_chat_message)
                                pbar.update(1)
                            if len(live_chat_messages) >= max_messages:
                                break
                        next_page_token = response.get('nextPageToken')
                        if not next_page_token or len(live_chat_messages) >= max_messages:
                            break

                        # Add a delay to avoid hitting rate limits
                        time.sleep(1)  # Adjust the delay as needed
                    except HttpError as e:
                        if e.resp.status == 403 and 'rateLimitExceeded' in e.content.decode():
                            retry_count += 1
                            if retry_count > max_retries:
                                st.error("Max retries exceeded. Stopping.")
                                break
                            st.warning(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            st.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
                            break
    except HttpError as e:
        st.error(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    return live_chat_messages

def generate_summary(transcript_text):
    """Generates a summary using the Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = ("Analyze the following YouTube comments or live chat messages. Identify the overall sentiment."
              " Provide a short summary of the comments/messages and any insights into the audience's reaction to the content."
              " In the end, give the shortest summary of the text."
              " Text given here: ")
    try:
        response = model.generate_content(prompt + transcript_text)
        return response.text
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        return "Error generating summary"

def analyze_sentiment(text):
    """Analyzes the overall sentiment of the text."""
    blob = TextBlob(text)
    return blob.sentiment

def main():
    st.title("YouTube Comments/Live Chat Summarizer and Analyzer")
    
    if 'combined_text' not in st.session_state:
        st.session_state.combined_text = ""
    
    video_url = st.text_input("Enter the YouTube video URL:")
    
    if video_url:
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("Invalid YouTube URL")
            return

        fetch_choice = st.selectbox("Select an option:", ["Comments", "Live Chat"])

        if st.button("Fetch and Summarize"):
            if fetch_choice == 'Comments':
                comments = fetch_comments(video_id, max_comments=777)
                st.session_state.combined_text = "\n".join(comments)
            elif fetch_choice == 'Live Chat':
                live_chat_messages = fetch_live_chat(video_id, max_messages=777)
                st.session_state.combined_text = "\n".join(live_chat_messages)

            if st.session_state.combined_text:
                st.info("Generating summary...")
                summary = generate_summary(st.session_state.combined_text)
                st.subheader("Summary:")
                st.write(summary)

                st.info("Analyzing sentiment...")
                sentiment = analyze_sentiment(st.session_state.combined_text)
                st.subheader("Sentiment Analysis:")
                st.write(f"Polarity: {sentiment.polarity}, Subjectivity: {sentiment.subjectivity}")

    if st.session_state.combined_text:
        user_question = st.text_input("Ask a question based on the comments/live chat:", key="user_question")

        if st.button("Ask"):
            if user_question:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = (f"Based on the following YouTube comments or live chat messages, answer the user's question: {user_question}"
                          f"\nComments/Live Chat: {st.session_state.combined_text}")
                try:
                    response = model.generate_content(prompt)
                    st.subheader("Answer:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Error generating response: {e}")

if __name__ == "__main__":
    main()  
