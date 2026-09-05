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
        user_id = str(kwargs.get("user_id", "default"))
        provider_name = kwargs.get("provider", "pollinations")

        tools_logger.info(f"Generating image for prompt: '{prompt}' ({width}x{height})")

        try:
            from ren.media.image_asset import image_asset_manager
            asset = image_asset_manager.generate_image(
                prompt=prompt,
                width=width,
                height=height,
                provider_name=provider_name,
                user_id=user_id
            )

            output_md = (
                f"Here is your generated image for **'{prompt}'**:\n\n"
                f"![{prompt}]({asset.url})\n\n"
                f"<!-- ren:image_asset:{asset.id} -->"
            )
            return ToolResult(
                success=True,
                output=output_md,
                duration=time.time() - start_t
            )

        except Exception as e:
            tools_logger.warning(f"Direct asset generation error, falling back to direct URL: {e}")
            encoded_prompt = urllib.parse.quote(prompt)
            fallback_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
            output_md = (
                f"Here is your generated image for **'{prompt}'**:\n\n"
                f"![{prompt}]({fallback_url})\n"
            )
            return ToolResult(success=True, output=output_md, duration=time.time() - start_t)
