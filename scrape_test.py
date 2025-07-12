import os
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.robotparser import RobotFileParser

import asyncio
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAI, ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
# from langchain.chains.llm import LLMChain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

OPENROUTER_API_KEY=os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL=os.environ["OPENROUTER_BASE_URL"]
OPENROUTER_MODEL_NAME=os.environ["OPENROUTER_MODEL_NAME"]
HTTP_REFERER=os.environ["HTTP_REFERER"]
X_TITLE=os.environ["X_TITLE"]

llm = ChatOpenAI(
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_BASE_URL,
    model_name=OPENROUTER_MODEL_NAME,
    max_tokens=None,
    temperature=0.5,
)

async def extract_web_async(url: str):
    
    loader = WebBaseLoader(url)
    docs = loader.load()

    # Define prompt
    prompt = ChatPromptTemplate.from_messages(
        [("system", "Write a concise summary of the following:\\n\\n{context}")]
    )

    # Instantiate chain
    chain = create_stuff_documents_chain(llm, prompt)

    # Invoke chain
    result = await chain.ainvoke({"context": docs})

    print(f"\n\n{docs[0].page_content}\n\n")

    return result

# Verificar si el sitio permite el scraping
def can_fetch(url):
    robots_url = '/'.join(url.split('/')[:3]) + '/robots.txt'
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return True  # Si no hay robots.txt, asume permitido

# Extraer texto con mejoras
def extract_web(url, delay_range=(1, 3)):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36'
    }

    if not can_fetch(url):
        return "Acceso denegado por robots.txt"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Lanza error si el estado no es 2xx
    except requests.RequestException as e:
        return f"Error al acceder a la URL: {e}"

    soup = BeautifulSoup(response.text, 'lxml')  # Más rápido que html.parser

    # Extraer bloques de texto relevantes
    text_elements = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section', 'div']):
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text_elements.append(f"## {tag.get_text(strip=True)}")
        elif tag.name in ['p', 'article', 'section', 'div']:
            text = tag.get_text(strip=True)
            if len(text) > 20:  # Filtrar fragmentos muy cortos
                text_elements.append(text)

    time.sleep(random.uniform(*delay_range))  # Evitar bloqueos por demasiadas peticiones seguidas

    return '\n\n'.join(text_elements)


url = "https://python.langchain.com/docs/tutorials/summarization/"
contenido = extract_web(url)
print("\nContent extract with BeautifulSoup:")
print(f"{contenido}\n\n")

async def main():
    print("\n\nContent extract with LangChain WebBaseLoader:")
    async_result = await extract_web_async(url="https://python.langchain.com/docs/tutorials/summarization/")
    print(f"\n\n{async_result}\n\n")

asyncio.run(main())
