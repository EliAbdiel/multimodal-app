import os
from dotenv import load_dotenv
import chainlit as cl
# from langchain_community.chat_models import ChatOllama
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from topic_classifier import classify_intent
from generate_images import generate_image
from scrape_links import scrape_link, scrape_web_async
# from search_duckduckgo_queries import agent_results_text
from little_deepresearch import agent_results_text, content_as_pdf
from youtube_video_transcribe import youtube_transcribe


load_dotenv(override=True)

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.1,  # <-- Super slow! We can only make a request once every 10 seconds!!
    check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
    max_bucket_size=10,  # Controls the maximum burst size.
)

async def process_user_message(user_message: cl.Message) -> None:
    """
    Processes a user message and provides a response using a language model or performs specific actions based on the intent.

    Args:
        user_message (cl.Message): The message sent by the user to be processed.

    Workflow:
    - If no active chain exists in the user session:
        1. Classifies the user's intent (web scraping, Searches, general chat, or video transcribe).
        2. Executes the corresponding action:
            - Generate an image (if 'image' intent).
            - Scrapes content from a URL (if 'scraper' intent).
            - Searches using DuckDuckGo (if 'search' intent).
            - Answers a general chat question (if 'chat' intent).
            - Transcribe a video from YouTube (if 'youtube_transcribe' intent)

    - If an active chain exists:
        - Processes the message using the existing chain and retrieves the response and source documents.
    """
    chain = cl.user_session.get("chain")
    # user_message = user_message.content.strip()

    # Handle explicit commands
    if user_message.command:
        if handler := command_mapping.get(user_message.command):
            await handler(user_message)
        return

    # Handle detected intents
    if chain is None:
        intent = await classify_intent(user_message=user_message.content)
        print('Detected intent:', intent)

        for keyword, handler in intent_mapping.items():
            if keyword in intent:
                await handler(user_message)
                return
        return

    # Handle chain conversation
    response = await chain.ainvoke(user_message.content)
    await cl.Message(content=response["answer"]).send()

    # Legacy code for handling intents (commented out)
    # if chain is None:
    #     intent = await classify_intent(user_message=user_message)
        
    #     if 'image' in intent:
    #         print('Your intent is: ', intent)
            
    #         await cl.Message(content="Image Generation Selected! \nYou've chosen to generate an image.").send()
            
    #         generated_image_path = await generate_image(user_message=user_message)
    #         image_element = cl.Image(name="Generated Image", path=generated_image_path)
            
    #         await cl.Message(content="Here's the generated image!", elements=[image_element]).send()

    #     elif 'scraper' in intent:
    #         print('Your intent is: ', intent)

    #         await cl.Message(content="You've chosen to scrape link.\n Please hold on while I work on it!").send()
    #         scraped_link = await scrape_link(user_message=user_message)
    #         # link_element = cl.File(name='Extracted link', path=str(scraped_link))
            
    #         await cl.Message(content=scraped_link).send()
            
    #     elif 'search' in intent:
    #         print('Your intent is: ', intent)
            
    #         await cl.Message(content="Search on the Web Browser Selected!\n Please wait while I work on it!").send()
    #         search_results = await agent_results_text(user_message=user_message)
    #         search_link = await content_as_pdf(content=search_results)
    #         pdf_element = cl.Pdf(name="research_report", path=str(search_link))

    #         # formatted_results = ""
    #         # for index, result in enumerate(search_results[:5], start=1):  
    #         #     title = result['title']
    #         #     href = result['href']
    #         #     body = result['body']
    #         #     formatted_results += f"{index}. **Title:** {title}\n**Link:** {href}\n**Description:** {body}\n\n"

    #         await cl.Message(content=search_results, elements=[pdf_element]).send()
                          
    #     elif 'chat' in intent:
    #         print('Your intent is: ', intent)
                
    #         model = ChatGoogleGenerativeAI(
    #                     model=os.environ["GEMINI_MODEL"],
    #                     google_api_key=os.environ["GEMINI_API_KEY"],
    #                     temperature=0.5,
    #                 ) 
    #         answer = await model.ainvoke(user_message)
    #         print("\nChat Usage Metadata:")
    #         print(answer.usage_metadata)
            
    #         await cl.Message(content=answer.content).send()

    #     elif 'video_transcribe' in intent:
    #         print('Your intent is: ', intent)

    #         transcribe = await youtube_transcribe(user_message=user_message)
    #         await cl.Message(content=transcribe).send()


    # else:
    #     if type(chain) == str:
    #         pass

    #     else:
    #         cb = cl.AsyncLangchainCallbackHandler()  
    #         response = await chain.ainvoke(user_message, callbacks=[cb])
    #         # response = await chain.ainvoke(
    #         #     {
    #         #         "question": user_message, 
    #         #         "input": user_message
    #         #     },  # Include both keys
    #         #     # config=cl.run_config,
    #         #     # session_id=str(cl.user_session.id)  # Pass session ID for history tracking
    #         #     {"configurable": {"session_id": str(id(cl.user_session))}}  # Use object id as a unique identifier
    #         # )
    #         # print("\nQ-A Usage Metadata:")
    #         # print(f"{response.response_metadata}\n")
    #         print(f"\n {response}\n")
    #         answer = response["answer"]
            
    #         await cl.Message(content=answer).send()


async def image_generation(user_message: cl.Message) -> None:
    """Handle image generation workflow."""
    await cl.Message(content="Image Generation Selected! \nYou've chosen to generate an image.").send()
    generated_image_path = await generate_image(user_message=user_message.content)
    image_element = cl.Image(name="Generated Image", path=generated_image_path)
    await cl.Message(content="Here's the generated image!", elements=[image_element]).send()

async def link_scraping(user_message: cl.Message) -> None:
    """Handle web scraping workflow."""
    await cl.Message(content="You've chosen to scrape a link.\nPlease hold on while I work on it!").send()
    scraped_content = await scrape_link(user_message=user_message)
    await cl.Message(content=scraped_content).send()

async def web_search(user_message: cl.Message) -> None:
    """Handle web search and research report workflow."""
    await cl.Message(content="Search on the Web Browser Selected!\nPlease wait while I work on it!").send()
    search_results = await agent_results_text(user_message=user_message.content)
    
    if len(search_results) > 100:
        pdf_path = await content_as_pdf(content=search_results)
        pdf_element = cl.Pdf(name="research_report", path=str(pdf_path))
        await cl.Message(content=search_results, elements=[pdf_element]).send()
    else:
        await cl.Message(content=search_results).send()

async def chat_conversation(user_message: cl.Message) -> None:
    """Handle conversational AI workflow."""
    await cl.Message(content="Conversational AI Selected!\nPlease wait while I work on it!").send()
    model = ChatGoogleGenerativeAI(
        model=os.environ["GEMINI_MODEL"],
        rate_limiter=rate_limiter,
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.5,
    )
    answer = await model.ainvoke(user_message.content)
    
    if not answer:
        await cl.Message(content="I encountered an error. Please try again later!").send()
        return

    print("\nChat Usage Metadata:", answer.usage_metadata)
    await cl.Message(content=answer.content).send()

async def youtube_transcription(user_message: cl.Message) -> None:
    """Handle YouTube video transcription workflow."""
    await cl.Message(content="Transcribe YouTube video Selected!\nPlease hold on while I work on it!").send()
    transcript = await youtube_transcribe(user_message=user_message)
    await cl.Message(content=transcript).send()

# Define the command mapping for easy access
command_mapping = {
    "Picture": image_generation,
    "Scrape": link_scraping,
    "Search": web_search,
    "Chat": chat_conversation,
    "YouTube": youtube_transcription
}

# Define the intent mapping for easy access
intent_mapping = {
    'image': image_generation,
    'scraper': link_scraping,
    'search': web_search,
    'chat': chat_conversation,
    'video_transcribe': youtube_transcription
}
