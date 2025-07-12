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
