import os
import asyncio
import re

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
    print(f"\n{response}\n")
    # for each in response.candidates[0].content.parts:
    #     print(each.text)
    result = "\n".join(each.text for each in response.candidates[0].content.parts if hasattr(each, "text"))
    
    return result


async def extract_context_and_url(user_message: str):
    pattern = re.compile(r"""(?ix)
        (?P<context>.*?)
        (?P<url>https?://[^\s]+)
        (?P<context_after>.*)?
    """)

    match = pattern.search(user_message.strip())

    if not match:
        return [user_message.strip()]
   
    url = match.group("url").strip()
    before = match.group("context").strip()
    after = match.group("context_after").strip() if match.group("context_after") else ""

    context = f"{before} {after}".strip()

    if context:
        return [context, url]
    else:
        return [url]
   
async def main(user_message: str):
    context_and_url = await extract_context_and_url(user_message)
    print(f"\nExtracted context and URL: {context_and_url}\n")
    print(type(context_and_url))
    if len(context_and_url) == 2:
        print(f"\nContext: {context_and_url[0]}")
        print(f"\nURL: {context_and_url[1]}")
        answer = await url_context(user_message)
        print(f"\nAnswer: {answer}")
    else:
        print(f"\nSingle content: {context_and_url[0]}")




# user_message = 'Resume este tema "Embeddings" https://docs.spring.io/spring-ai/reference/concepts.html'
user_message = "Extract the key points from this LangChain documentation page https://python.langchain.com/docs/tutorials/summarization/"

# if __name__ == "__main__":
#   asyncio.run(main(user_message))
