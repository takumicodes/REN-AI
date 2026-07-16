import os
import json
from memory import load_memory, save_memory

def learn_from_chats():
    # Path to chats folder
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chats_dir = os.path.join(workspace_dir, "chats")
    os.makedirs(chats_dir, exist_ok=True)
    
    chat_files = [f for f in os.listdir(chats_dir) if f.endswith(".txt") or f.endswith(".json")]
    
    if not chat_files:
        speak("No conversation files found in the chats folder, sir. Please place text files there for me to read.")
        print("[DONE]")
        return
        
    speak(f"Found {len(chat_files)} conversation logs. Analyzing content for memory updates...")
    
    learned_facts = []
    
    for filename in chat_files:
        filepath = os.path.join(chats_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Simple heuristic to extract potential project or details Sadiq is working on
                if "project" in line.lower() or "working on" in line.lower():
                    words = line.split()
                    for word in words:
                        word_clean = word.strip(".,!?\"'")
                        # Look for capitalized proper nouns (excluding generic terms and names)
                        if word_clean and word_clean[0].isupper() and word_clean.lower() not in ["sadiq", "ren", "project", "working", "the", "this", "python", "javascript", "c++"]:
                            learned_facts.append(f"Project: {word_clean}")
                            
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            
    if learned_facts:
        memory = load_memory()
        if "learned_from_chats" not in memory:
            memory["learned_from_chats"] = []
            
        new_facts = []
        for fact in learned_facts:
            if fact not in memory["learned_from_chats"]:
                memory["learned_from_chats"].append(fact)
                new_facts.append(fact)
                
        if new_facts:
            save_memory(memory)
            speak(f"Analysis complete. I have updated my memory with new facts: {', '.join(new_facts[:3])}")
        else:
            speak("Analysis complete. I didn't find any new facts that were not already in my memory.")
    else:
        speak("Analysis complete, but I couldn't extract any structured facts from the conversations.")
        
    print("[DONE]")

if __name__ == "__main__":
    if "speak" not in globals():
        from voice import speak
    learn_from_chats()
