# import os
# from dotenv import load_dotenv
# import chainlit as cl
from ddgs import DDGS
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

async def text(
    keywords: str,
    max_results: int | None = None,
    ) -> list[dict[str, str, str]]:
    """
    Performs a text search on DuckDuckGo with specified query parameters.

    Args:
        keywords (str): The search keywords.
        max_results (int | None): Maximum number of results to retrieve. If None, defaults to the first response only.

    Returns:
        list[dict]: A list of dictionaries containing the search results.
    """
    with DDGS() as ddgs:
        results = list(ddgs.text(keywords=keywords, max_results=5))
    return results

