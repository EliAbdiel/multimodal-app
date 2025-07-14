import os
# import time
# import random
# import itertools
# import requests
import aiohttp
import asyncio
import httpx
import chainlit as cl

from dotenv import load_dotenv
from ddgs import DDGS
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from search_duckduckgo_queries import duckduckgo_search
from bs4 import BeautifulSoup

load_dotenv()

RESULTS_PER_QUESTION = 3

ddgs = DuckDuckGoSearchAPIWrapper()

tavily_search = TavilySearchAPIWrapper(tavily_api_key=os.environ["TAVILY_API_KEY"])

# def scrape_link(url):
#   try:
#     response = requests.get(url)
    
#     if response.status_code == 200:
#       # Parse the content of the page using BeautifulSoup
#       soup = BeautifulSoup(response.text, 'html.parser')
        
#       # Extract all text from the webpage
#       text = soup.get_text(separator=' ', strip=True)

#       return text
#     else:
#       return f"Failed to scrape the webpage. Status code: {response.status_code}"
#   except Exception as e:
#     print(f"An error occurred: {e}")
#     return f"Failed to scrape the webpage. Error: {e}"

# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

async def scrape_link_async(url):
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
  }
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as response:
        if response.status == 200:
          # Parse the content of the page using BeautifulSoup
          html = await response.text()
          soup = BeautifulSoup(html, 'html.parser')
            
          # Extract all text from the webpage
          text = soup.get_text(separator=' ', strip=True)

          return text
        else:
          return f"Failed to scrape the webpage. Status code: {response.status}"
  except Exception as e:
    print(f"An error occurred while I scrape the webpage: {e}")
    return f"Failed to scrape the webpage. Error: {e}"

# async def scrape_link_async(url):
# 	# Create an async HTTP client
# 	async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
# 		try:
# 			# Fetch the content
# 			response = await client.get(url)
# 			response.raise_for_status()
# 			# Convert HTML to markdown if successful
# 			if response.status_code == 200:
# 				# Parse the content of the page using BeautifulSoup
# 				html = await response.text()
# 				soup = BeautifulSoup(html, 'html.parser')
			
# 				# Extract all text from the webpage
# 				text = soup.get_text(separator=' ', strip=True)

# 				return text
				
# 			else:
# 				return f"Failed to scrape the webpage. Status code: {response.status}"
# 		except Exception as e:
# 			# Handle any exceptions during fetch
# 			print(f"An error occurred: {e}")
# 			return f"Failed to scrape the webpage. Error: {e}"

def flatten_list_of_list(list_of_list):
  content = []
  for sublist in list_of_list:
    content.append("\n\n".join(sublist))
  return "\n\n".join(content)

async def web_search(query: str, num_results: int = RESULTS_PER_QUESTION):
  try:
    results = await cl.make_async(DDGS().text)(keywords=query, timelimit='y', max_results=num_results)
    # print(f"\nresult is a list of dicts: \n{results}\n")
    urls = [r["href"] for r in results]
    print(f"\nURLs found: {urls}\n")
    return urls
  except Exception as e:
    print(f"An error occurred: {e}")
    return []

async def web_search_with_tavily(query: str, num_results: int = RESULTS_PER_QUESTION):
  try:
    result = await tavily_search.results_async(query=query, max_results=num_results)
    print(f"\nresult is a list of dicts: \n{result}\n")
    urls = [item["url"] for item in result if "url" in item]
    return urls
  except Exception as e:
    print(f"An error occurred: {e}")
    return []
  
async def web_search_async(query: str, num_results: int = RESULTS_PER_QUESTION):
  results = await duckduckgo_search(search_queries=query, num_results=num_results)
  print(f"\nweb_search_async results: {results}\n")
  return results


# async def web_search_async(query: str, num_results: int = RESULTS_PER_QUESTION, max_retries: int = 3, delay: float = 2.0):
#   for attempt in range(max_retries):
#     try:
#       # Add a delay between attempts
#       if attempt > 0:
#         await asyncio.sleep(delay * attempt)
      
#       # loop = asyncio.get_event_loop()
#       # results = await loop.run_in_executor(None, lambda: ddgs.results(query, num_results))
#       results = await cl.make_async(ddgs.results)(query, num_results)
#       return [r["link"] for r in results]
#     except Exception as e:
#       if attempt == max_retries - 1:
#         print(f"Error after {max_retries} attempts: {e}")
#         return []
#       print(f"Attempt {attempt + 1} failed: {e}. Retrying...")

# async def web_search_async(query: str, num_results: int = RESULTS_PER_QUESTION):
#   # to run it in a thread pool
#   loop = asyncio.get_event_loop()
#   results = await loop.run_in_executor(None, lambda: ddgs.results(query, num_results))
#   return [r["link"] for r in results]