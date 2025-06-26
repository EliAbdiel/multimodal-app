import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

async def youtube_transcribe(url: str) -> str:
    """
    This function takes a YouTube video URL as input and uses the Gemini model to:
    1. Transcribe the audio content from the video
    2. Generate timestamps for key events
    3. Provide visual descriptions of what's happening in the video
    
    Args:
        url (str): The URL of the YouTube video to analyze
        
    Returns:
        str: A text response containing the transcription, timestamps and visual descriptions
    """

    prompt = """Transcribe the audio from this video, giving timestamps for salient events in the video. 
        Also provide visual descriptions."""

    response = client.models.generate_content(
        model=os.environ["GEMINI_2_5_MODEL"],
        contents=types.Content(
            parts=[
                types.Part(
                    file_data=types.FileData(file_uri=url)
                ),
                types.Part(text=prompt)
            ]
        )
    )

    return response.text
