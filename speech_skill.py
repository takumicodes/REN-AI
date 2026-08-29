import pyttsx3

class SpeechSkill:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Setting properties for a clearer, more natural voice
        self.engine.setProperty('rate', 175)    # Speed of speech
        self.engine.setProperty('volume', 1.0)  # Volume level

    def speak(self, text):
        print(f"[Ren Speaking]: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

if __name__ == "__main__":
    # Test the skill
    ren_voice = SpeechSkill()
    ren_voice.speak("Skill initialized. I can now speak. Hello, I am Ren, created by Sadiq.")