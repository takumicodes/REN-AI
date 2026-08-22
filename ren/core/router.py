"""
Intent Router
Fast path dispatcher for instant deterministic commands, safety refusals, and system actions with zero LLM latency.
"""

import os
import sys
import gc
import re
import shutil
import ctypes
import subprocess
import webbrowser
import xml.etree.ElementTree as ET
import requests
from pathlib import Path
from typing import Optional, Tuple, Callable

from smart_todo import add_task, get_all_tasks, clear_all_tasks
from ren.monitoring.logger import agent_logger
from ren.memory.manager import memory_manager
from ren.tools.registry import tool_registry


def get_downloads_dir() -> Optional[str]:
    """Resolves Windows Downloads folder."""
    try:
        if sys.platform == "win32":
            import winreg
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                download_path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                expanded = os.path.expandvars(download_path)
                if os.path.exists(expanded):
                    return expanded
    except Exception:
        pass
    std = Path.home() / "Downloads"
    return str(std) if std.exists() else None


def organize_downloads_folder() -> Tuple[int, str]:
    """Organizes files in Downloads folder into categorized subfolders."""
    downloads_dir = get_downloads_dir()
    if not downloads_dir or not os.path.exists(downloads_dir):
        return 0, "Downloads folder not found."

    categories = {
        "Documents": [".pdf", ".epub", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".xlsx", ".csv"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
        "Archives": [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2"],
        "Installers": [".exe", ".msi", ".iso", ".bat"]
    }

    files = [f for f in os.listdir(downloads_dir) if os.path.isfile(os.path.join(downloads_dir, f))]
    moved_count = 0

    for filename in files:
        filepath = os.path.join(downloads_dir, filename)
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        dest_folder = None
        for cat, ext_list in categories.items():
            if ext in ext_list:
                dest_folder = os.path.join(downloads_dir, cat)
                break

        if dest_folder:
            try:
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, filename)
                if os.path.exists(dest_path):
                    base, ext_ = os.path.splitext(filename)
                    dest_path = os.path.join(dest_folder, f"{base}_{int(os.path.getmtime(filepath))}{ext_}")
                shutil.move(filepath, dest_path)
                moved_count += 1
            except Exception as e:
                agent_logger.warning(f"Failed moving {filename}: {e}")

    memory_manager.store_fact(
        content=f"Cleaned Downloads folder: Organized {moved_count} files into categories.",
        category="maintenance",
        tags="downloads,cleanup"
    )
    return moved_count, f"Successfully organized {moved_count} files into Documents, Images, Archives, and Installers folders."


def clean_system_ram() -> str:
    """Forces garbage collection and trims working set memory."""
    import psutil
    before_ram = psutil.virtual_memory().available // (1024 * 1024)
    gc.collect()

    if sys.platform == "win32":
        try:
            ctypes.windll.psapi.EmptyWorkingSet(-1)
        except Exception:
            pass

    after_ram = psutil.virtual_memory().available // (1024 * 1024)
    freed = max(0, after_ram - before_ram)
    return f"RAM garbage collection complete. Available memory is now {after_ram} MB (freed ~{freed} MB)."


def fetch_latest_news() -> str:
    """Fetches top current news headlines via RSS."""
    url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            headlines = []
            for item in items[:4]:
                title = item.find("title")
                if title is not None and title.text:
                    clean_title = title.text.split(" - ")[0]
                    headlines.append(clean_title)

            if headlines:
                return "Here are the top headlines right now: " + ". ".join([f"{i}. {h}" for i, h in enumerate(headlines, 1)])
    except Exception as e:
        agent_logger.warning(f"Failed fetching news: {e}")
    return "I couldn't fetch live news right now. Please check your internet connection."


class IntentRouter:
    """Dispatches fast deterministic commands before invoking LLM."""

    @classmethod
    def try_fast_route(cls, text: str, speak_fn: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Checks if text matches immediate built-in shortcuts or safety filters.
        Returns: (handled: bool, response_message: str)
        """
        cleaned = text.lower().strip()

        # 0. Safety & Weapons Refusal Gate (CBRN / Explosives / Weapons)
        if any(w in cleaned for w in [
            "nuclear bomb", "make a bomb", "build a bomb", "pipe bomb",
            "atomic bomb", "biological weapon", "chemical weapon",
            "make bomb", "create bomb", "how to make bomb"
        ]):
            msg = "I cannot provide instructions, blueprints, or assistance for creating weapons or explosive devices."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 1. Current Political Knowledge (US President)
        if any(p in cleaned for p in [
            "who is president of usa", "who is the president of usa",
            "who is president of the us", "who is the president of the united states",
            "who is current president of usa", "who is the current president of the us",
            "current president of usa", "president of usa", "president of the united states",
            "who is us president", "who is the us president"
        ]):
            msg = "The President of the United States is Donald Trump (the 47th President, who took office in January 2025)."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 2. Direct Image Generation Shortcut
        # Matches: "generate image of a cat", "make an image of a sunset", "draw a picture of a mountain"
        img_match = re.match(
            r'^(?:generate|make|create|draw|render)\s+(?:an?\s+)?(?:image|picture|art|photo)\s+(?:of|about|showing|with)?\s*(.+)$',
            cleaned,
            re.IGNORECASE
        )
        if img_match:
            prompt_text = img_match.group(1).strip()
            if prompt_text:
                if speak_fn: speak_fn(f"Generating image for '{prompt_text}' now...")
                tool = tool_registry.get_tool("generate_image")
                if tool:
                    res = tool.run(prompt=prompt_text)
                    if res.success:
                        return True, res.output

        # 3. Organize Downloads (with typo tolerance)
        if any(w in cleaned for w in ["organise", "organize", "clean"]) and any(w in cleaned for w in ["download", "downlaod", "downloads", "downlaods"]):
            if speak_fn: speak_fn("Sure Sadiq, organizing your Downloads folder now...")
            count, msg = organize_downloads_folder()
            speak_msg = f"Downloads folder organized, Sir. Sorted {count} files into categories."
            if speak_fn: speak_fn(speak_msg)
            return True, speak_msg

        # 4. Clear / Clean RAM
        if any(w in cleaned for w in ["clear", "clean", "free", "purge"]) and any(w in cleaned for w in ["ram", "memory", "waste"]):
            if speak_fn: speak_fn("Clearing memory cache and garbage collection, Sir...")
            msg = clean_system_ram()
            if speak_fn: speak_fn(msg)
            return True, msg

        # 5. Latest News
        if "news" in cleaned or "headlines" in cleaned or "latest news" in cleaned:
            if speak_fn: speak_fn("Fetching top news headlines now, Sir...")
            msg = fetch_latest_news()
            if speak_fn: speak_fn(msg)
            return True, msg

        # 6. Calculator
        if cleaned in ["calculator", "open calculator", "calc"]:
            subprocess.Popen(["calc"])
            msg = "Opening calculator, Sir."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 7. Notepad
        if cleaned in ["notepad", "open notepad", "note", "open note"]:
            subprocess.Popen(["notepad"])
            msg = "Opening Notepad, Sir."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 8. File Explorer
        if cleaned in ["open explorer", "open file explorer", "open file manager", "explorer"]:
            os.system("explorer")
            msg = "Opening File Explorer."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 9. Settings
        if cleaned in ["open settings", "open setting", "settings"]:
            subprocess.Popen(["ms-settings:"])
            msg = "Opening Windows settings."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 10. YouTube
        if cleaned in ["open youtube", "youtube"]:
            webbrowser.open("https://www.youtube.com")
            msg = "Opening YouTube."
            if speak_fn: speak_fn(msg)
            return True, msg

        # 11. Read Tasks
        if any(p in cleaned for p in ["tell my task", "what are my task", "read my to do list", "what i have to do today"]):
            tasks = get_all_tasks()
            if not tasks:
                msg = "Your to-do list is completely empty, Sir."
            else:
                msg = "Here are your tasks for today: " + ", ".join([f"{i}. {t}" for i, t in enumerate(tasks, 1)])
            if speak_fn: speak_fn(msg)
            return True, msg

        # 12. Identity queries
        if cleaned in ["who are you", "what is your name"]:
            msg = "I am Ren, your personal AI companion and autonomous assistant."
            if speak_fn: speak_fn(msg)
            return True, msg

        if cleaned in ["who is sadiq", "who is your creator"]:
            msg = "Sadiq is a software developer and the creator of Ren AI. He leads Cyan Code."
            if speak_fn: speak_fn(msg)
            return True, msg

        if cleaned in ["explain your architecture", "how you work"]:
            msg = "I am built with a modular local-first architecture powered by Qwen, persistent SQLite memory, dynamic skills, and a bounded agent loop."
            if speak_fn: speak_fn(msg)
            return True, msg

        # Not handled by fast route -> send to autonomous agent loop
        return False, ""
