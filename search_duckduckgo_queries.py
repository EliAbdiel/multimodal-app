# import os
# from dotenv import load_dotenv
# import chainlit as cl
import asyncio
import random
import time
import httpx

from markdownify import markdownify
from ddgs import DDGS
from typing import List, Optional, Dict, Any, Union, Literal, Annotated, cast
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_openai import ChatOpenAI
# from langchain.chains.summaize import load_summarize_chain
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# load_dotenv()

# OPENROUTER_API_KEY=os.environ["OPENROUTER_API_KEY"]
# OPENROUTER_BASE_URL=os.environ["OPENROUTER_BASE_URL"]
# OPENROUTER_MODEL_NAME=os.environ["OPENROUTER_MODEL_NAME"]
# HTTP_REFERER=os.environ["HTTP_REFERER"]
# X_TITLE=os.environ["X_TITLE"]

# llm = ChatOpenAI(
#     openai_api_key=OPENROUTER_API_KEY,
#     openai_api_base=OPENROUTER_BASE_URL,
#     model_name=OPENROUTER_MODEL_NAME,
#     max_tokens=None,
#     temperature=0.5,
# )

async def duckduckgo_search(search_queries: List[str], num_results: int):
    """Perform searches using DuckDuckGo with retry logic to handle rate limits
    
    Args:
        search_queries (List[str]): List of search queries to process
        
    Returns:
        str: A formatted string of search results
    """
    
    async def process_single_query(query):
        # Execute synchronous search in the event loop's thread pool
        loop = asyncio.get_event_loop()
        
        def perform_search():
            max_retries = 3
            retry_count = 0
            backoff_factor = 2.0
            last_exception = None
            
            while retry_count <= max_retries:
                try:
                    results = []
                    with DDGS() as ddgs:
                        # Change query slightly and add delay between retries
                        if retry_count > 0:
                            # Random delay with exponential backoff
                            delay = backoff_factor ** retry_count + random.random()
                            print(f"Retry {retry_count}/{max_retries} for query '{query}' after {delay:.2f}s delay")
                            time.sleep(delay)
                            
                            # Add a random element to the query to bypass caching/rate limits
                            modifiers = ['about', 'info', 'guide', 'overview', 'details', 'explained']
                            modified_query = f"{query} {random.choice(modifiers)}"
                        else:
                            modified_query = query
                        
                        # Execute search
                        ddg_results = list(ddgs.text(keywords=query, max_results=num_results, timelimit='y'))
                        
                        # Format results
                        for i, result in enumerate(ddg_results):
                            results.append({
                                'title': result.get('title', ''),
                                'url': result.get('href', ''),
                                'content': result.get('body', ''),
                                'score': 1.0 - (i * 0.1),  # Simple scoring mechanism
                                'raw_content': result.get('body', '')
                            })
                        
                        # Return successful results
                        return {
                            'query': query,
                            'follow_up_questions': None,
                            'answer': None,
                            'images': [],
                            'results': results
                        }
                except Exception as e:
                    # Store the exception and retry
                    last_exception = e
                    retry_count += 1
                    print(f"DuckDuckGo search error: {str(e)}. Retrying {retry_count}/{max_retries}")
                    
                    # If not a rate limit error, don't retry
                    if "Ratelimit" not in str(e) and retry_count >= 1:
                        print(f"Non-rate limit error, stopping retries: {str(e)}")
                        break
            
            # If we reach here, all retries failed
            print(f"All retries failed for query '{query}': {str(last_exception)}")
            # Return empty results but with query info preserved
            return {
                'query': query,
                'follow_up_questions': None,
                'answer': None,
                'images': [],
                'results': [],
                'error': str(last_exception)
            }
            
        return await loop.run_in_executor(None, perform_search)

    # Process queries with delay between them to reduce rate limiting
    search_docs = []
    urls = []
    titles = []
    for i, query in enumerate(search_queries):
        # Add delay between queries (except first one)
        if i > 0:
            delay = 2.0 + random.random() * 2.0  # Random delay 2-4 seconds
            await asyncio.sleep(delay)
        
        # Process the query
        result = await process_single_query(query)
        search_docs.append(result)
        
        # Safely extract URLs and titles from results, handling empty result cases
        if result['results'] and len(result['results']) > 0:
            for res in result['results']:
                if 'url' in res and 'title' in res:
                    urls.append(res['url'])
                    titles.append(res['title'])
    
    # If we got any valid URLs, scrape the pages
    if urls:
        # return await scrape_pages(titles, urls)
        return urls
    else:
        # return "No valid search results found. Please try different search queries or use a different search API."
        return []


async def scrape_pages(titles: List[str], urls: List[str]) -> str:
    """
    Scrapes content from a list of URLs and formats it into a readable markdown document.
    
    This function:
    1. Takes a list of page titles and URLs
    2. Makes asynchronous HTTP requests to each URL
    3. Converts HTML content to markdown
    4. Formats all content with clear source attribution
    
    Args:
        titles (List[str]): A list of page titles corresponding to each URL
        urls (List[str]): A list of URLs to scrape content from
        
    Returns:
        str: A formatted string containing the full content of each page in markdown format,
             with clear section dividers and source attribution
    """
    
    # Create an async HTTP client
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        pages = []
        
        # Fetch each URL and convert to markdown
        for url in urls:
            try:
                # Fetch the content
                response = await client.get(url)
                response.raise_for_status()
                
                # Convert HTML to markdown if successful
                if response.status_code == 200:
                    # Handle different content types
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type:
                        # Convert HTML to markdown
                        markdown_content = markdownify(response.text)
                        pages.append(markdown_content)
                    else:
                        # For non-HTML content, just mention the content type
                        pages.append(f"Content type: {content_type} (not converted to markdown)")
                else:
                    pages.append(f"Error: Received status code {response.status_code}")
        
            except Exception as e:
                # Handle any exceptions during fetch
                pages.append(f"Error fetching URL: {str(e)}")
        
        # Create formatted output
        formatted_output = f"Search results: \n\n"
        
        for i, (title, url, page) in enumerate(zip(titles, urls, pages)):
            formatted_output += f"\n\n--- SOURCE {i+1}: {title} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += f"FULL CONTENT:\n {page}"
            formatted_output += "\n\n" + "-" * 80 + "\n"
        
    return formatted_output

# queries=[
#   "RAG Retrieval-Augmented Generation definición técnica y aplicaciones recientes",
#   "RAG Meta AI investigación y publicaciones científicas",
#   "RAG Hugging Face ejemplos de código y documentación oficial"
# ]

# async def main():
#   # question = "Encuentra informacion sobre RAG (Retrieval-Augmented Generation)"
#   results = await duckduckgo_search(search_queries=queries)
#   print(f"\n{results}\n")

# if __name__ == "__main__":
#   asyncio.run(main())

# async def text(
#     keywords: str,
#     max_results: int | None = None,
#     ) -> list[dict[str, str, str]]:
#     """
#     Performs a text search on DuckDuckGo with specified query parameters.

#     Args:
#         keywords (str): The search keywords.
#         max_results (int | None): Maximum number of results to retrieve. If None, defaults to the first response only.

#     Returns:
#         list[dict]: A list of dictionaries containing the search results.
#     """
#     with DDGS() as ddgs:
#         results = list(ddgs.text(keywords=keywords, max_results=5))
#     return results

# async def agent_results_text(user_message: str) -> list[dict[str, str, str]]:
    # """
    # Asynchronously retrieves text search results from DuckDuckGo based on user input.

    # Args:
    #     user_message (str): The query string entered by the user.

    # Returns:
    #     list[dict]: A list of search result dictionaries containing information like title, link, and description.
    # """
    # with DDGS() as ddgs:
    #     results = list(ddgs.text(keywords=user_message, timelimit='y', max_results=5))
    # print(f"Results:\n\n{results}")

    # urls = [item['href'] for item in results]

    # loader = WebBaseLoader(urls)
    # docs = loader.load()
    # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    # split_docs = text_splitter.split_documents(docs)
    # summarize_chain = load_summarize_chain(llm, chain_type="map_reduce")

    # summaries=[]
    # for i, doc in enumerate(split_docs):
    #     url = doc.metadata['source']
        
    #     summary = await summarize_chain.ainvoke([doc])
    #     summaries.append({
    #         "summary": summary["output_text"].strip()
    #     })

    # print(f"Summary for \n{summaries}\n")

    # return results


