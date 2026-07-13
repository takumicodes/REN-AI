import edge_tts
import asyncio
import pygame

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
    asyncio.run(edge_speak(text))