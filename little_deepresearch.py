import os
import asyncio
import json
from dotenv import load_dotenv
# from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
# from langchain.schema.output_parser import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from prompts import generate_webpage_summary_template, generate_search_queries_prompt, generate_research_report_prompt
from web_search import scrape_link_async, flatten_list_of_list, web_search_async, web_search_with_tavily

load_dotenv()

SUMMARY_TEMPLATE = generate_webpage_summary_template()
SUMMARY_PROMPT = ChatPromptTemplate.from_template(SUMMARY_TEMPLATE)

llm_openai = ChatOpenAI(
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    openai_api_base=os.environ["OPENROUTER_BASE_URL"],
    model_name=os.environ["OPENROUTER_MODEL_NAME"],
    max_tokens=None,
    temperature=0.0,
)

# llm_ollama = ChatOllama(model="llama3.2:1b")

llm_google = ChatGoogleGenerativeAI(
    model=os.environ["GEMINI_MODEL"],
    google_api_key=os.environ["GEMINI_API_KEY"],
    temperature=0.3,
)

llm_google_v2 = ChatGoogleGenerativeAI(
    model=os.environ["GEMINI_MODEL"],
    google_api_key=os.environ["GEMINI_API_KEY_V2"],
    temperature=0.3,
)

async def scrape_and_summarize(url_data):
  text = await scrape_link_async(url_data["url"])
  text = text[:10000]
  summary = await llm_google_v2.ainvoke(SUMMARY_PROMPT.format(text=text, question=url_data["question"]))
  return f"URL: {url_data['url']}\n\nSummary: {summary}"

async def process_search_results(data):
  urls = await web_search_with_tavily(data["question"])
  if not urls:
    print(f"No results could be obtained for the search: {data['question']}")
    return []

  tasks = []
  for url in urls:
    tasks.append(scrape_and_summarize({"question": data["question"], "url": url}))
  
  try:
    return await asyncio.gather(*tasks)
  except Exception as e:
    print(f"Error processing results: {e}")
    return []

SEARCH_PROMPT = ChatPromptTemplate.from_messages(
  [
    (
      "user", generate_search_queries_prompt()
    )
  ]
)

async def safe_json_loads(text):
  try:
    start = text.find('[')
    end = text.find(']')
    if start != -1 and end != -1:
      json_str = text[start:end+1]
      return json.loads(json_str)
    return json.loads(text)
  except json.JSONDecodeError as e:
    print(f"Initial JSON parse failed: {e}")
    try:
      fixed_json = await llm_google.ainvoke(f"Fix this JSON and return only the corrected version: {text}")
      return json.loads(fixed_json.content.strip())
    except Exception as fix_error:
      print(f"Failed to fix JSON: {fix_error}")
      return []

async def process_search_questions(question):
  search_output = await llm_google.ainvoke(SEARCH_PROMPT.format(question=question))
  print("Raw output from LLM: ", search_output.content.strip())
  queries = await safe_json_loads(search_output.content.strip())
  tasks = [process_search_results({"question": q}) for q in queries]
  return await asyncio.gather(*tasks)

WRITER_SYSTEM_PROMPT = "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."

RESEARCH_REPORT_PROMPT = generate_research_report_prompt()

prompt = ChatPromptTemplate.from_messages(
  [
    ("system", WRITER_SYSTEM_PROMPT),
    ("user", RESEARCH_REPORT_PROMPT)
  ]
)

async def generate_report(question):
  research_results = await process_search_questions(question)
  context = flatten_list_of_list(research_results)
  report = await llm_google_v2.ainvoke(prompt.format(context=context, question=question))
  return report

async def agent_results_text(user_message: str):
  # question = "Encuentra informacion sobre RAG (Retrieval-Augmented Generation)"
  results = await generate_report(user_message)
  print(f"\n\n{results}\n")
  return results

# if __name__ == "__main__":
#   asyncio.run(main())

# scrape_and_summarize_chain = RunnablePassthrough.assign(summary=RunnablePassthrough.assign(
#   text=lambda x: scrape_link(x["url"])[:10000]
# ) | SUMMARY_PROMPT | llm_ollama | StrOutputParser()) | (lambda x: f"URL: {x['url']}\n\nSummary: {x['summary']}")

# web_search_chain = RunnablePassthrough.assign(
#   urls=lambda x: web_search(x["question"])
# ) | (lambda x: [{"question": x["question"], "url": url} for url in x["urls"]]) | scrape_and_summarize_chain.map()

# SEARCH_PROMPT = ChatPromptTemplate.from_messages(
#   [
#     (
#       "user", generate_search_queries_prompt()
#     )
#   ]
# )

# def safe_json_loads(text):
#   try:
#     return json.loads(text)
#   except json.JSONDecodeError:
#     print("Retrying JSON parsing...")
#     return json.loads(llm_openai.invoke(f"Fix this JSON: {text}").content)

# search_question_chain = SEARCH_PROMPT | llm_openai | StrOutputParser() | (lambda x: print("Raw output from LLM:", x) or x) | RunnableLambda(safe_json_loads)

# full_research_chain = search_question_chain | (lambda x: [{"question": q} for q in x]) | web_search_chain.map()

# WRITER_SYSTEM_PROMPT = "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."

# RESEARCH_REPORT_PROMPT = generate_research_report_prompt()

# prompt = ChatPromptTemplate.from_messages(
#   [
#     ("system", WRITER_SYSTEM_PROMPT),
#     ("user", RESEARCH_REPORT_PROMPT)
#   ]
# )

# chain = RunnablePassthrough.assign(
#   context = full_research_chain | flatten_list_of_list) | prompt | llm_ollama | StrOutputParser()

# results = chain.invoke({"question": "Busca informacion sobre RAG (Retrieval-Augmented Generation)"})

# print(f"\n\n{results}\n")
