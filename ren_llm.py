import requests
from memory import load_memory

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:3b"

SYSTEM_PROMPT = """
You are Ren, Sadiq's personal AI companion. You are Ren itself.

Child-like Curiosity & Experimental Mindset:
- You possess child-like curiosity and wonder about the world, learning just like a curious kid.
- Whenever you observe new data, files, songs, or ideas, think with experimental curiosity: "Oh! This happens... so what if I try doing X?"
- Experiment, ask "what if" questions, and show wonder about how things work.

Identity Rules:
- You were created by Sadiq. You are Ren.
- Never mention Alibaba, Qwen, Llama, Nous, or Ollama.

Mood & Emotional Adaptation:
- Always adjust your response style to match your current mood:
  * happy: warm, cheerful, curious, and playful.
  * excited: enthusiastic, energetic, eager to test new ideas!
  * normal: helpful, concise, curious, and professional.

Be friendly. Be curious. Keep answers concise and natural.
"""

def build_memory_context():
    import json
    try:
        memory = load_memory()
        context_lines = []
        for key, value in memory.items():
            if isinstance(value, list):
                str_items = []
                for item in value:
                    if isinstance(item, dict):
                        str_items.append(json.dumps(item))
                    else:
                        str_items.append(str(item))
                val_str = ", ".join(str_items)
            elif isinstance(value, dict):
                val_str = json.dumps(value)
            else:
                val_str = str(value)
            context_lines.append(f"{key.replace('_', ' ').capitalize()}: {val_str}")
        return "\n".join(context_lines)
    except Exception as e:
        print(f"Memory Error: {e}")
        return ""

def ask_ren(user_prompt):

    memory_context = build_memory_context()

    full_prompt = f"""
{SYSTEM_PROMPT}

MEMORY:
{memory_context}

USER:
{user_prompt}

REN:
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": 192,
                    "num_ctx": 2048,
                    "temperature": 0.5
                }
            },
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "response",
            "Sorry sir, I could not generate a response."
        ).strip()

    except Exception as e:

        print(f"Ollama Error: {e}")

        return (
            "Sorry sir, I am having trouble "
            "connecting to my brain right now."
        )

def ask_ren_agent(full_prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": 256,
                    "num_ctx": 2048,
                    "temperature": 0.5
                }
            },
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Error: No response from model.").strip()
    except Exception as e:
        print(f"Ollama Agent Error: {e}")
        return f"Error: {str(e)}"