import os
import asyncio

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

tools = []
tools.append(Tool(url_context=types.UrlContext))
tools.append(Tool(google_search=types.GoogleSearch()))

async def url_context(user_message: str):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_message,
        config=GenerateContentConfig(
            tools=tools,
            response_modalities=["TEXT"],
        )
    )

    for each in response.candidates[0].content.parts:
        print(each.text)


user_message = 'Resume este video de youtube en 3 lineas: https://youtu.be/Huy-Gn4RtGQ?si=TCBo-fVBxNWXdDh6'

if __name__ == "__main__":
  asyncio.run(url_context(user_message))