import os
from dotenv import load_dotenv
import chainlit as cl
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
import io
import wave
import numpy as np
import audioop
from scipy.signal import butter, filtfilt, wiener
from scipy.io import wavfile
try:
    import librosa
    import noisereduce as nr
    ADVANCED_AUDIO = True
except ImportError:
    ADVANCED_AUDIO = False
    print("Install librosa and noisereduce for enhanced audio processing: pip install librosa noisereduce")

# from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from create_chain_retriever import create_chain_retriever
from process_user_files import handle_files_from_audio_message
from topic_classifier import classify_intent
from scrape_links import scrape_link
from search_duckduckgo_queries import agent_results_text
from process_text_to_speech import speak_async


load_dotenv(override=True)

# Enhanced audio processing constants
OPTIMAL_SAMPLE_RATE = 16000  # Optimal for speech recognition
SILENCE_THRESHOLD = 1500  # Lowered for better sensitivity
SILENCE_TIMEOUT = 1200  # Reduced timeout
MIN_SPEECH_DURATION = 300  # Reduced minimum duration
# AUDIO_CHUNK_SIZE = 1024
ENERGY_SMOOTHING_FACTOR = 0.8  # Increased smoothing

async def process_audio_chunk(chunk: cl.InputAudioChunk) -> None:
    """
    Handles incoming audio chunks and stores them in a buffer for further processing.

    Args:
        chunk (cl.InputAudioChunk): The audio data to process.

    Returns:
        BytesIO: The buffer containing the audio data.
    """
    audio_chunks = cl.user_session.get("audio_chunks")

    if chunk.isStart: # Ensure audio_chunks is initialized if it's the start
        if audio_chunks is None:
            audio_chunks = []
            cl.user_session.set("audio_chunks", audio_chunks)
        # Set mime type at the start of a new audio stream
        cl.user_session.set("audio_mime_type", f"audio/{chunk.mimeType.split('/')[-1]}") # Store the mimeType

    if audio_chunks is not None:
        audio_chunk_data = np.frombuffer(chunk.data, dtype=np.int16)
        audio_chunks.append(audio_chunk_data)

    # If this is the first chunk, initialize timers and state
    if chunk.isStart:
        cl.user_session.set("last_elapsed_time", chunk.elapsedTime)
        cl.user_session.set("is_speaking", True)
        return

    audio_chunks = cl.user_session.get("audio_chunks")
    last_elapsed_time = cl.user_session.get("last_elapsed_time")
    silent_duration_ms = cl.user_session.get("silent_duration_ms")
    is_speaking = cl.user_session.get("is_speaking")

    # Calculate the time difference between this chunk and the previous one
    time_diff_ms = chunk.elapsedTime - last_elapsed_time
    cl.user_session.set("last_elapsed_time", chunk.elapsedTime)

    # Compute the RMS (root mean square) energy of the audio chunk
    audio_energy = audioop.rms(
        chunk.data, 2
    )  # Assumes 16-bit audio (2 bytes per sample)

    # Apply exponential smoothing to reduce noise spikes
    previous_energy = cl.user_session.get("previous_energy", audio_energy)
    smoothed_energy = 0.7 * previous_energy + 0.3 * audio_energy
    cl.user_session.set("previous_energy", smoothed_energy)

    if smoothed_energy < SILENCE_THRESHOLD:
        # Audio is considered silent
        silent_duration_ms += time_diff_ms
        cl.user_session.set("silent_duration_ms", silent_duration_ms)
        if silent_duration_ms >= SILENCE_TIMEOUT and is_speaking:
            cl.user_session.set("is_speaking", False)
            await process_audio() # Call process_audio, it will set the session variable
    else:
        # Audio is not silent, reset silence timer and mark as speaking
        # Enhanced speech detection
        speech_duration = cl.user_session.get("speech_duration_ms", 0)
        speech_duration += time_diff_ms
        cl.user_session.set("speech_duration_ms", speech_duration)
        
        cl.user_session.set("silent_duration_ms", 0)
        if not is_speaking and speech_duration >= MIN_SPEECH_DURATION:
            cl.user_session.set("is_speaking", True)


async def process_audio() -> None:
    """Enhanced audio processing with noise reduction and optimization"""
    if audio_chunks := cl.user_session.get("audio_chunks"):
        # Concatenate all chunks
        concatenated = np.concatenate(list(audio_chunks))
        
        # Apply comprehensive audio preprocessing
        processed_audio = await preprocess_audio(concatenated)
        
        # Create optimized WAV file
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(OPTIMAL_SAMPLE_RATE)
            wav_file.writeframes(processed_audio.tobytes())
        
        wav_buffer.seek(0)
        cl.user_session.set("audio_chunks", [])
        
        # Enhanced duration check
        with wave.open(wav_buffer, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            
        if duration <= 0.5:  # More lenient minimum duration
            print(f"Audio too short ({duration:.2f}s), please try again.")
            cl.user_session.set("audio_buffer", None)
            return
            
        wav_buffer.seek(0)
        cl.user_session.set("audio_buffer", wav_buffer)
        cl.user_session.set("audio_mime_type", "audio/wav")
        print(f"Processed audio: {duration:.2f}s at {rate}Hz")
    else:
        cl.user_session.set("audio_buffer", None)

async def preprocess_audio(audio_data):
    """Comprehensive audio preprocessing pipeline"""
    # Convert to float for processing
    audio_float = audio_data.astype(np.float32) / 32768.0
    
    if ADVANCED_AUDIO:
        # Advanced preprocessing with librosa
        try:
            # Resample to optimal rate if needed
            if len(audio_float) > 0:
                audio_float = librosa.resample(audio_float, orig_sr=24000, target_sr=OPTIMAL_SAMPLE_RATE)
            
            # Noise reduction
            audio_float = nr.reduce_noise(y=audio_float, sr=OPTIMAL_SAMPLE_RATE, stationary=False)
            
            # Normalize volume
            audio_float = librosa.util.normalize(audio_float)
            
            # Trim silence from beginning and end
            audio_float, _ = librosa.effects.trim(audio_float, top_db=20)
            
        except Exception as e:
            print(f"Advanced preprocessing failed, using basic: {e}")
            audio_float = apply_basic_preprocessing(audio_float)
    else:
        audio_float = apply_basic_preprocessing(audio_float)
    
    # Convert back to int16
    return (audio_float * 32767).astype(np.int16)

def apply_basic_preprocessing(audio_data):
    """Basic audio preprocessing without external libraries"""
    # Normalize volume
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val * 0.8
    
    # Apply enhanced noise reduction
    audio_data = apply_enhanced_noise_reduction(audio_data)
    
    return audio_data

def apply_enhanced_noise_reduction(audio_data):
    """Enhanced noise reduction with multiple filters"""
    # High-pass filter to remove low-frequency noise
    nyquist = OPTIMAL_SAMPLE_RATE / 2
    low_cutoff = 80 / nyquist  # Remove frequencies below 80Hz
    high_cutoff = 8000 / nyquist  # Remove frequencies above 8kHz
    
    # Band-pass filter for speech frequencies
    b_low, a_low = butter(4, low_cutoff, btype='high')
    b_high, a_high = butter(4, high_cutoff, btype='low')
    
    filtered_audio = filtfilt(b_low, a_low, audio_data)
    filtered_audio = filtfilt(b_high, a_high, filtered_audio)
    
    # Apply Wiener filter for additional noise reduction
    try:
        filtered_audio = wiener(filtered_audio, noise=0.1)
    except:
        pass  # Fallback if Wiener filter fails
    
    return filtered_audio

async def convert_audio_to_wav(audio_buffer: BytesIO, mime_type: str) -> BytesIO:
    """
    Converts audio data to WAV format.

    Args:
        audio_buffer (BytesIO): The buffer containing audio data.
        mime_type (str): The MIME type of the audio.

    Returns:
        BytesIO: The buffer containing the WAV audio data.
    """
    audio_buffer.seek(0)
    audio_segment = AudioSegment.from_file(audio_buffer, format=mime_type.split('/')[1])
    buffer_wav = io.BytesIO()
    audio_segment.export(buffer_wav, format='wav')
    buffer_wav.seek(0)
    
    return buffer_wav

async def audio_answer(elements: list = None) -> None:
    """Enhanced audio transcription with multiple recognition engines"""

    # memory = cl.user_session.get("memory")

    if elements is None:
        elements = []
        
    recognizer = sr.Recognizer()
    audio_buffer = cl.user_session.get("audio_buffer")
    
    if not audio_buffer:
        await cl.Message(content="Could not retrieve audio for processing. Please try recording again.").send()
        return

    audio_buffer.seek(0)
    
    # Optimized recognizer settings
    recognizer.energy_threshold = 200  # Lower threshold for better sensitivity
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6  # Shorter pause detection
    recognizer.phrase_threshold = 0.3  # Minimum phrase length
    recognizer.non_speaking_duration = 0.5  # Non-speaking duration

    try:
        transcription = await transcribe_with_enhanced_fallback(recognizer, audio_buffer)
    
        if not transcription:
            await cl.Message(content="Could not understand the audio. Please try speaking more clearly or check your microphone.").send()
            return

        # memory.chat_memory.add_user_message(transcription)

        # Add confidence scoring
        confidence_msg = "" if len(transcription) > 10 else " (Low confidence - please speak more clearly)"
        
        chain = await create_chain_retriever(texts=transcription, source_prefix="text/plain")
        
        await cl.Message(content=f"{transcription}{confidence_msg}", elements=elements).send()
        
        if elements:           
              
            for file in elements:
                
                if file.mime.startswith("image/"):
                    await handle_files_from_audio_message(elements=elements, user_message=transcription)
                
                else: 
                    cb = await handle_files_from_audio_message(elements=elements, user_message=transcription) 
                    
                    response = await chain.ainvoke(transcription, callbacks=[cb])
                    answer = response["answer"]
                    
                    await cl.Message(content=answer).send()
                    # memory.chat_memory.add_ai_message(answer)
                    # await speak_async(answer=answer)
                       
        else:
            intent = await classify_intent(user_message=transcription)
            
            if 'scraper' in intent:
                print('Your intent is: ', intent)
                
                scraped_link = await scrape_link(user_message=transcription)
                link_element = cl.File(name='Extracted link', path=scraped_link)
                
                await cl.Message(content='Your link has been successfully extracted.\n Click here to access the content directly!: ', elements=[link_element]).send()
 
            elif 'search' in intent:
                print('Your intent is: ', intent)
                                
                await cl.Message(content="Search Selected!\n You've chosen to search on the DuckDuckGo Web Browser.").send()
                
                search_results = await agent_results_text(user_message=transcription)
                formatted_results = ""
                
                for index, result in enumerate(search_results[:5], start=1):  
                    title = result['title']
                    href = result['href']
                    body = result['body']
                    formatted_results += f"{index}. **Title:** {title}\n**Link:** {href}\n**Description:** {body}\n\n"
                
                await cl.Message(content=formatted_results).send()
                # memory.chat_memory.add_ai_message(formatted_results)
                                
            elif 'chat' in intent:
                print('Your intent is: ', intent)
                
                model = ChatGoogleGenerativeAI(
                            model=os.environ["GEMINI_MODEL"],
                            google_api_key=os.environ["GEMINI_API_KEY"],
                            temperature=0.5,
                        )
                answer = await model.ainvoke(transcription)
                
                await cl.Message(content=answer.content).send()
                # memory.chat_memory.add_ai_message(answer.content)  
                # await speak_async(answer=answer.content) 

    except sr.UnknownValueError:
        await cl.Message(content="Unable to recognize speech. Please try again with clearer pronunciation.").send()
    except Exception as e:
        await cl.Message(content=f"Audio processing error: {str(e)}").send()

async def transcribe_with_enhanced_fallback(recognizer, audio_buffer):
    """Enhanced transcription with multiple engines and languages"""
    transcription_attempts = []
    
    try:
        with sr.AudioFile(audio_buffer) as source:
            # Enhanced ambient noise adjustment
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio = recognizer.record(source)
            
            # Primary: Google Speech Recognition with multiple languages
            google_languages = ["es-ES", "es-MX", "es-AR", "en-US"]
            for lang in google_languages:
                try:
                    result = recognizer.recognize_google(audio, language=lang, show_all=False)
                    if result and len(result.strip()) > 2:
                        transcription_attempts.append((result, f"Google-{lang}"))
                        print(f"Transcription success with Google-{lang}: {result}")
                        return result
                except (sr.UnknownValueError, sr.RequestError) as e:
                    print(f"Google-{lang} failed: {e}")
                    continue
            
            # Fallback: Sphinx (offline)
            try:
                result = recognizer.recognize_sphinx(audio, language="es-ES")
                if result and len(result.strip()) > 2:
                    transcription_attempts.append((result, "Sphinx"))
                    print(f"Transcription success with Sphinx: {result}")
                    return result
            except (sr.UnknownValueError, sr.RequestError) as e:
                print(f"Sphinx failed: {e}")
            
            # Additional fallback: Try with different audio processing
            try:
                # Adjust audio gain and try again
                audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                # Amplify quiet audio
                amplified = np.clip(audio_data * 2, -32768, 32767).astype(np.int16)
                amplified_audio = sr.AudioData(amplified.tobytes(), audio.sample_rate, audio.sample_width)
                
                result = recognizer.recognize_google(amplified_audio, language="es-ES")
                if result and len(result.strip()) > 2:
                    print(f"Transcription success with amplified audio: {result}")
                    return result
            except Exception as e:
                print(f"Amplified audio transcription failed: {e}")
                    
    except Exception as e:
        print(f"Transcription error: {e}")
        
    # Return best attempt if any
    if transcription_attempts:
        best_attempt = max(transcription_attempts, key=lambda x: len(x[0]))
        print(f"Using best attempt from {best_attempt[1]}: {best_attempt[0]}")
        return best_attempt[0]
        
    return None