import os
from dotenv import load_dotenv
# import asyncio
import httpx
# import hashlib
# import time
from pathlib import Path
# import requests
from bs4 import BeautifulSoup
import html2text
import aiofiles
import uuid

from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
# from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatOpenAI(
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    openai_api_base=os.environ["OPENROUTER_BASE_URL"],
    model_name=os.environ["OPENROUTER_MODEL_NAME"],
    max_tokens=None,
    temperature=0.3,
)

async def scrape_web_async(url: str):
    
    loader = WebBaseLoader(url)
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
            print(f"Processed URL {url}, sussessfully extracted content.")
        return result
    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        return "I encountered an error while processing the URL (e.g., malformed URL). Please try again later!"

async def scrape_link(user_message: str) -> str:
    """
    Scrapes HTML from a URL Web Page, converts it to Markdown format,
    and saves it in a .txt file.

    Args:
        user_message (str): The URL to scrape.

    Returns:
        str: Path to the text file containing the extracted Markdown content.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(user_message)
        response.raise_for_status()
        html_content = response.text

    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(['script', 'style', 'img', 'a', 'nav', 'footer', 'header', 'form', 'button', 'noscript']):
        tag.decompose()

    texto_limpio = soup.get_text(separator='\n')
    lineas = [line.strip() for line in texto_limpio.splitlines() if line.strip()]
    texto_limpio = '\n'.join(lineas)

    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = True
    text_content = markdown_converter.handle(texto_limpio)

    output_dir = Path("extracted_data")
    output_dir.mkdir(exist_ok=True)

    # url_hash = hashlib.md5(user_message.encode()).hexdigest()
    # timestamp = int(time.time())
    txt_file_path = output_dir / f"{uuid.uuid4()}.txt"

    async with aiofiles.open(txt_file_path, mode="w", encoding="utf-8") as f:
        await f.write(text_content)

    return str(txt_file_path)

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
