"""
Skill: Image Generation
Generates AI images from visual text prompts, downloads them locally, and displays Markdown preview.
"""

import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def generate_image(prompt: str, output_path: str = None) -> str:
    """Generates an image from a prompt and saves to disk."""
    if not prompt:
        return "Please provide a prompt for image generation."
    
    encoded = urllib.parse.quote(prompt.strip())
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=768&nologo=true"
    
    out_dir = Path("data/generated_images")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not output_path:
        output_path = str(out_dir / f"img_{int(time.time())}.jpg")
        
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) REN-AI/2.5"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return f"Generated image for **'{prompt}'**:\n\n![{prompt}]({url})\n\n*(Saved to `{output_path}`)*"
    except Exception as e:
        return f"Generated image for **'{prompt}'**:\n\n![{prompt}]({url})"


def main():
    if len(sys.argv) > 1:
        p = " ".join(sys.argv[1:])
    else:
        p = "a futuristic neon city"
    print(generate_image(p))


if __name__ == "__main__":
    main()