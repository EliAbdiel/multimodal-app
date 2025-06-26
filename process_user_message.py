import os
from dotenv import load_dotenv
import chainlit as cl
# from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from topic_classifier import classify_intent
from scrape_links import scrape_link
from search_duckduckgo_queries import agent_results_text
from youtube_video_transcribe import youtube_transcribe


load_dotenv(override=True)

async def process_user_message(user_message: cl.Message) -> None:
    """
    Processes a user message and provides a response using a language model or performs specific actions based on the intent.

    Args:
        user_message (cl.Message): The message sent by the user to be processed.
        model_name (str): The model selected with the chat_profile choice.

    Workflow:
    - If no active chain exists in the user session:
        1. Classifies the user's intent (web scraping, Searches, general chat, or video transcribe).
        2. Executes the corresponding action:
            - Scrapes content from a URL (if 'scraper' intent).
            - Searches using DuckDuckGo (if 'search' intent).
            - Answers a general chat question (if 'chat' intent).
            - Transcribe a video from YouTube (if 'video_transcribe' intent)

    - If an active chain exists:
        - Processes the message using the existing chain and retrieves the response and source documents.
    """


    chain = cl.user_session.get("chain")
    user_message = user_message.content.strip()


    if chain is None:
        intent = await classify_intent(user_message=user_message)
        
        if 'scraper' in intent:
            print('Your intent is: ', intent)

            scraped_link = await scrape_link(user_message=user_message)
            link_element = cl.File(name='Extracted link', path=str(scraped_link))
            
            await cl.Message(content='Your link has been successfully extracted.\n Click here to access the content directly!: ', elements=[link_element]).send()
            
        elif 'search' in intent:
            print('Your intent is: ', intent)
                        
            await cl.Message(content="You've chosen to search on the DuckDuckGo Web Browser.\n The first 5 links will be displayed.").send()
            search_results = await agent_results_text(user_message=user_message)

            formatted_results = ""
            for index, result in enumerate(search_results[:5], start=1):  
                title = result['title']
                href = result['href']
                body = result['body']
                formatted_results += f"{index}. **Title:** {title}\n**Link:** {href}\n**Description:** {body}\n\n"

            await cl.Message(content=formatted_results).send()
                          
        elif 'chat' in intent:
            print('Your intent is: ', intent)
                
            model = ChatGoogleGenerativeAI(
                        model=os.environ["GEMINI_MODEL"],
                        google_api_key=os.environ["GEMINI_API_KEY"],
                        temperature=0.5,
                    ) 
            answer = await model.ainvoke(user_message)
            
            await cl.Message(content=answer.content).send()

        elif 'video_transcribe' in intent:
            print('Your intent is: ', intent)

            transcribe = await youtube_transcribe(url=user_message)
            await cl.Message(content=transcribe).send()


    else:
        if type(chain) == str:
            pass

        else:  
            # response = await chain.ainvoke(user_message)
            response = await chain.ainvoke(
                {"input": user_message},
                config=cl.run_config,
                session_id=str(cl.user_session.id)  # Pass session ID for history tracking
            )
            answer = response["answer"]
            
            await cl.Message(content=answer).send()

