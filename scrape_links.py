import os
import re
import httpx
import html2text
import aiofiles
import uuid
# import asyncio
# import hashlib
# import time
# import requests

from dotenv import load_dotenv
from pathlib import Path
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
# from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate
from google import genai
from google.genai import types
from google.genai.types import Tool, GenerateContentConfig

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

tools = []
tools.append(Tool(url_context=types.UrlContext))
tools.append(Tool(google_search=types.GoogleSearch()))

llm = ChatOpenAI(
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    openai_api_base=os.environ["OPENROUTER_BASE_URL"],
    model_name=os.environ["OPENROUTER_MODEL_NAME"],
    max_tokens=None,
    temperature=0.3,
)


async def scrape_link(user_message: str):
    context_and_url = await extract_context_and_url(user_message)
    print(f"\nExtracted context and URL: {context_and_url}\n")
    if len(context_and_url) == 2:
        answer = await url_context(user_message)
    else:
        answer = await scrape_web_async(user_message)
    
    return answer

async def url_context(user_message: str):
    try:
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
    except Exception as e:
        print(f"Error in url_context {user_message}: {e}")
        return "I encountered an error while processing the URL. Please try again later!"

async def scrape_web_async(user_message: str):
    
    loader = WebBaseLoader(user_message)
    # docs = loader.load()
    docs = []
    async for doc in loader.alazy_load():
        docs.append(doc)

    # Define prompt
    prompt = ChatPromptTemplate.from_template("Summarize this content: {context}")

    # Instantiate chain
    chain = create_stuff_documents_chain(llm, prompt)

    # Invoke chain
    result = await chain.ainvoke({"context": docs[:10000]})

    try:
        if result:
            print(f"Processed URL {user_message}, sussessfully extracted content.")
        return result
    except Exception as e:
        print(f"Error processing URL {user_message}: {e}")
        return "I encountered an error while processing the URL (e.g., malformed URL). Please try again later!"


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
    
# async def scrape_link(user_message: str) -> str:
#     """
#     Scrapes HTML from a URL Web Page, converts it to Markdown format,
#     and saves it in a .txt file.

#     Args:
#         user_message (str): The URL to scrape.

#     Returns:
#         str: Path to the text file containing the extracted Markdown content.
#     """
#     async with httpx.AsyncClient(timeout=10) as client:
#         response = await client.get(user_message)
#         response.raise_for_status()
#         html_content = response.text

#     soup = BeautifulSoup(html_content, "html.parser")

#     for tag in soup(['script', 'style', 'img', 'a', 'nav', 'footer', 'header', 'form', 'button', 'noscript']):
#         tag.decompose()

#     texto_limpio = soup.get_text(separator='\n')
#     lineas = [line.strip() for line in texto_limpio.splitlines() if line.strip()]
#     texto_limpio = '\n'.join(lineas)

#     markdown_converter = html2text.HTML2Text()
#     markdown_converter.ignore_links = True
#     text_content = markdown_converter.handle(texto_limpio)

#     output_dir = Path("extracted_data")
#     output_dir.mkdir(exist_ok=True)

    # url_hash = hashlib.md5(user_message.encode()).hexdigest()
    # timestamp = int(time.time())
    # txt_file_path = output_dir / f"{uuid.uuid4()}.txt"

    # async with aiofiles.open(txt_file_path, mode="w", encoding="utf-8") as f:
    #     await f.write(text_content)

    # return str(txt_file_path)

#     response = requests.get(user_message)
#     soup = BeautifulSoup(response.content, "html.parser")
    
#     html_content = soup.prettify()

#     markdown_converter = html2text.HTML2Text()
#     markdown_converter.ignore_links = False
#     text_content = markdown_converter.handle(html_content)

#     output_dir = Path("extracted_data")
#     output_dir.mkdir(exist_ok=True)

#     txt_file_path = output_dir / "extracted_link.txt"
#     with txt_file_path.open(mode="w", encoding="utf-8") as txt_file:
#         txt_file.write(text_content)
        
#     file_path = str(txt_file_path)

#     return file_path
