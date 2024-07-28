from django.shortcuts import render
from django.http import JsonResponse
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

# Hardcoded API key
genai.configure(api_key = "your api key")


prompt = """You are a YouTube video summarizer and note maker. You will be taking the transcript text 
and summarizing the entire video and providing the summary and notes. Please provide the summary 
and notes of the text given here: """

question_prompt = """You are an intelligent assistant. Answer the following question based on the video content: """

def index(request):
    return render(request, 'transcript/index.html')

def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[1].split("&")[0]
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'hi', 'mr'])
        transcript_text = " ".join([entry["text"] for entry in transcript.fetch()])
        return transcript_text
    except NoTranscriptFound:
        return "No transcript found"
    except Exception as e:
        return str(e)

def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt + transcript_text)
    return response.text

def generate_question_response(transcript_text, question):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(question_prompt + transcript_text + " Question: " + question)
    return response.text

def get_notes(request):
    youtube_link = request.GET.get('youtube_link')
    if youtube_link:
        transcript_text = extract_transcript_details(youtube_link)
        if "No transcript found" in transcript_text or "Error" in transcript_text:
            return JsonResponse({'error': transcript_text})
        summary = generate_gemini_content(transcript_text, prompt)
        return JsonResponse({'summary': summary})
    return JsonResponse({'error': 'Invalid YouTube link'})

def ask_question(request):
    youtube_link = request.GET.get('youtube_link')
    question = request.GET.get('question')
    if youtube_link and question:
        transcript_text = extract_transcript_details(youtube_link)
        if "No transcript found" in transcript_text or "Error" in transcript_text:
            return JsonResponse({'error': transcript_text})
        answer = generate_question_response(transcript_text, question)
        return JsonResponse({'answer': answer})
    return JsonResponse({'error': 'Invalid input'})
