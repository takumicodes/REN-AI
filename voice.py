import edge_tts
import asyncio
import pygame
import socket

def is_internet_available():
    try:
        # Check connection to Google Public DNS
        socket.setdefaulttimeout(1.5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

async def edge_speak(text):
    communicate = edge_tts.Communicate(
        text,
        voice="en-IN-PrabhatNeural"
    )

    await communicate.save("speech.mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("speech.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
    pygame.mixer.music.unload()

def speak(text):
    if is_internet_available():
        try:
            asyncio.run(edge_speak(text))
            return
        except Exception as e:
            print(f"Edge TTS connection error, falling back to offline SAPI5: {e}")
            
    # Offline fallback using pyttsx3 (SAPI5 on Windows)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Offline SAPI5 TTS failed: {e}")