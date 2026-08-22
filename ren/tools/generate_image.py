"""
REN Image Generation Tool
Generates high-resolution AI images from text descriptions using free, reliable generation APIs.
Saves images locally to data/generated_images/ and outputs rich Markdown image cards.
"""

import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.config.settings import settings
from ren.monitoring.logger import tools_logger, error_logger


class GenerateImageTool(BaseTool):
    """Generates images from text prompts and provides local file and markdown links."""

    name = "generate_image"
    description = (
        "Generate and render an image from a detailed visual text prompt. "
        "Use this whenever the user asks to generate, create, draw, or render an image."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Descriptive visual prompt for the image to generate."
            },
            "width": {
                "type": "integer",
                "description": "Image width in pixels (e.g. 768 or 1024). Default is 768."
            },
            "height": {
                "type": "integer",
                "description": "Image height in pixels (e.g. 768 or 1024). Default is 768."
            }
        },
        "required": ["prompt"]
    }

    def run(self, **kwargs) -> ToolResult:
        start_t = time.time()
        prompt = str(kwargs.get("prompt", "")).strip()
        if not prompt:
            return ToolResult(
                success=False,
                output="",
                error="Image prompt cannot be empty.",
                duration=time.time() - start_t
            )

        width = int(kwargs.get("width", 768))
        height = int(kwargs.get("height", 768))

        tools_logger.info(f"Generating image for prompt: '{prompt}' ({width}x{height})")

        # Create output directory
        images_dir = settings.PATHS.DATA_DIR / "generated_images"
        images_dir.mkdir(parents=True, exist_ok=True)

        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        
        timestamp = int(time.time())
        local_filename = f"image_{timestamp}.jpg"
        local_path = images_dir / local_filename

        try:
            # Download copy to local storage
            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) REN-AI/2.5"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                with open(local_path, "wb") as f:
                    f.write(resp.read())

            output_md = (
                f"Here is your generated image for **'{prompt}'**:\n\n"
                f"![{prompt}]({image_url})\n\n"
                f"*(Image saved locally to `{local_path}`)*"
            )
            return ToolResult(success=True, output=output_md, duration=time.time() - start_t)

        except Exception as e:
            tools_logger.warning(f"Direct download failed, providing direct URL: {e}")
            # Fallback to direct web URL
            output_md = (
                f"Here is your generated image for **'{prompt}'**:\n\n"
                f"![{prompt}]({image_url})\n"
            )
            return ToolResult(success=True, output=output_md, duration=time.time() - start_t)
