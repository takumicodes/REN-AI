import os
import subprocess

def generate_image(prompt, output_path):
    # Use a tool like Stable Diffusion or DALL-E to generate an image
    # Example using Stable Diffusion
    command = [
        "python",
        "stable_diffusion.py",
        "--prompt",
        prompt,
        "--output",
        output_path
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Image generated and saved to {output_path}")
    except Exception as e:
        print(f"Error generating image: {e}")

# Example usage
generate_image("A beautiful sunset over a mountain", "sunset.jpg")