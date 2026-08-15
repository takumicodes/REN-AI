import json
import os

# Database file to store your tasks permanently
TASKS_FILE = "todo_list.json"

def get_all_tasks():
    """Loads and returns all saved tasks."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []

def add_task(task_text):
    """Appends a single task to the JSON file database."""
    tasks = get_all_tasks()
    tasks.append(task_text)
    with open(TASKS_FILE, "w") as file:
        json.dump(tasks, file, indent=4)

def clear_all_tasks():
    """Clears out the entire list once you are done."""
    with open(TASKS_FILE, "w") as file:
        json.dump([], file)
