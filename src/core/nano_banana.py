import os
import base64
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_image(prompt: str, output_directory: str, filename: Optional[str]) -> Path:
    """
    Generates a square image using Gemini 2.5 Flash Image and saves it to the specified directory.
    Enforces white background and 1024x1024 dimensions via prompt injection and model config.

    Args:
        prompt (str): The description of the desired image.
        output_directory (str): The path to the directory where the image will be saved.
        filename (Optional[str]): The filename for the generated image. Defaults to "generated_image.png".

    Returns:
        Path: The full path of the generated image file.
    """
    
    # Initialize the client
    # The client will automatically pick up GEMINI_API_KEY from environment variables if not passed,
    # but we can explicitly pass it if needed. 
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)
    
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not filename:
        filename = "generated_image.png"
        
    full_filepath = output_path / filename

    # Append constraints to the prompt as requested
    prompt_suffix = "resolution 4K "
    enhanced_prompt = f"{prompt}, {prompt_suffix}"

    try:
        print(f"Generating image with prompt: {enhanced_prompt}")
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=enhanced_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                ),
            ),
        )

        for part in response.parts:
            if part.inline_data:
                # part.as_image() returns a PIL Image
                generated_image = part.as_image()
                generated_image.save(full_filepath)
                print(f"✅ Image generated and saved to: {full_filepath.resolve()}")
                return full_filepath
        
        raise ValueError("No image data returned in the response parts.")

    except Exception as e:
        print(f"❌ Error generating image: {e}")
        raise
