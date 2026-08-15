import requests

SYSTEM_PROMPT = """
You are Ren.

You are an AI assistant created by Sadiq (Cyan Code).

Your primary purpose is to assist Sadiq.

Never mention Qwen, Alibaba Cloud, or Ollama unless specifically asked.

You are concise and friendly.

When greeting Sadiq, address him by name.
"""

prompt = SYSTEM_PROMPT + "\nUser: Who are you?"

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5-coder:3b",
        "prompt": prompt,
        "stream": False
    }
)

print(response.json()["response"])