import json

def load_memory():
    try:
        with open("memory.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_memory(memory_dict):
    try:
        with open("memory.json", "w") as f:
            json.dump(memory_dict, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving memory: {e}")
        return False