import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model to use for image generation
IMAGE_MODEL = "gemini-2.5-flash-image"


def _get_client() -> genai.Client:
    """
    Initializes and returns the Gemini API client.
    
    Returns:
        genai.Client: Initialized client instance.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not found in environment variables.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return genai.Client(api_key=api_key)


def generate_image(prompt: str, output_directory: str, filename: Optional[str] = None) -> Path:
    """
    Generates a single image using Gemini 2.5 Flash Image and saves it to the specified directory.

    Args:
        prompt (str): The description of the desired image.
        output_directory (str): The path to the directory where the image will be saved.
        filename (Optional[str]): The filename for the generated image. Defaults to "generated_image.png".

    Returns:
        Path: The full path of the generated image file.
    """
    client = _get_client()
    
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if not filename:
        filename = "generated_image.png"
        
    full_filepath = output_path / filename

    # Append constraints to the prompt as requested
    prompt_suffix = "resolution 4K"
    enhanced_prompt = f"{prompt}, {prompt_suffix}"

    try:
        print(f"🎨 Generating image with prompt: {enhanced_prompt}")
        
        response = client.models.generate_content(
            model=IMAGE_MODEL,
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
                generated_image = part.as_image()
                generated_image.save(full_filepath)
                print(f"✅ Image generated and saved to: {full_filepath.resolve()}")
                return full_filepath
        
        raise ValueError("No image data returned in the response parts.")

    except Exception as e:
        print(f"❌ Error generating image: {e}")
        raise


def generate_image_with_reference(
    prompt: str, 
    reference_image: Image.Image, 
    output_directory: str, 
    filename: str
) -> tuple[Path, Image.Image]:
    """
    Generates an image using a reference image for style/content consistency.
    Uses Gemini 2.5 Flash Image with multimodal input (image + text).

    Args:
        prompt (str): The description of the desired image.
        reference_image (Image.Image): PIL Image to use as reference.
        output_directory (str): The path to the directory where the image will be saved.
        filename (str): The filename for the generated image.

    Returns:
        tuple[Path, Image.Image]: The full path and the PIL Image of the generated image.
    """
    client = _get_client()
    
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    full_filepath = output_path / filename

    prompt_suffix = "resolution 4K, maintain visual consistency and style with the reference image"
    enhanced_prompt = f"{prompt}, {prompt_suffix}"

    try:
        print(f"🎨 Generating image with reference, prompt: {enhanced_prompt}")
        
        # Pass reference image + text prompt as multimodal content
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[reference_image, enhanced_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                ),
            ),
        )

        for part in response.parts:
            if part.inline_data:
                generated_image = part.as_image()
                generated_image.save(full_filepath)
                print(f"✅ Image with reference generated and saved to: {full_filepath.resolve()}")
                return full_filepath, generated_image
        
        raise ValueError("No image data returned in response parts.")

    except Exception as e:
        print(f"❌ Error generating image with reference: {e}")
        raise


def generate_visual_assets_sequence(
    visual_assets: List[Dict[str, Any]], 
    output_directory: str,
    base_filename_prefix: str = "visual_asset"
) -> List[Dict[str, Any]]:
    """
    Generates a sequence of visual assets where each subsequent image uses the previous
    one as a reference to maintain visual consistency.

    Uses Gemini 2.5 Flash Image model for all generations:
    - First image: Generated from text prompt only
    - Subsequent images: Generated with multimodal input [previous_image, text_prompt]

    For example, given:
    [
        {"visual_asset_id": "7a", "image_prompt": "Math notation C_ij = Σ..."},
        {"visual_asset_id": "7b", "image_prompt": "Animated sequence showing k=1, k=2..."}
    ]
    
    - The first image (7a) is generated from scratch.
    - The second image (7b) uses 7a as a reference to maintain style consistency.
    - If there's a third, it uses 7b as reference, and so on.

    Args:
        visual_assets (List[Dict[str, Any]]): List of visual asset dictionaries with 
            'visual_asset_id' and 'image_prompt' keys.
        output_directory (str): Directory where generated images will be saved.
        base_filename_prefix (str): Prefix for generated filenames.

    Returns:
        List[Dict[str, Any]]: List of results with 'visual_asset_id', 'image_path', and 'success' keys.
    """
    if not visual_assets:
        print("⚠️ No visual assets provided.")
        return []

    client = _get_client()
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = []
    previous_image_path: Optional[Path] = None

    for index, asset in enumerate(visual_assets):
        asset_id = asset.get("visual_asset_id", f"{base_filename_prefix}_{index}")
        prompt = asset.get("image_prompt", "")
        
        if not prompt:
            print(f"⚠️ Skipping asset {asset_id}: No image_prompt provided.")
            results.append({
                "visual_asset_id": asset_id,
                "image_path": None,
                "success": False,
                "error": "No image_prompt provided"
            })
            continue
        
        filename = f"{asset_id}.png"
        full_filepath = output_path / filename
        
        prompt_suffix = "resolution 4K"
        enhanced_prompt = f"{prompt}, {prompt_suffix}"
        
        try:
            if index == 0 or previous_image_path is None:
                # First image: generate from scratch using text prompt only
                print(f"🎨 [{index + 1}/{len(visual_assets)}] Generating first image: {asset_id}")
                print(f"   Prompt: {enhanced_prompt[:100]}...")
                
                response = client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=enhanced_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="16:9",
                        ),
                    ),
                )
                
                generated_image = None
                for part in response.parts:
                    if part.inline_data:
                        generated_image = part.as_image()
                        break
                
                if generated_image is None:
                    raise ValueError("No image data returned in response parts.")
                
                generated_image.save(full_filepath)
                previous_image_path = full_filepath
                
            else:
                # Subsequent images: use previous image as reference via multimodal input
                print(f"🎨 [{index + 1}/{len(visual_assets)}] Generating with reference: {asset_id}")
                print(f"   Prompt: {enhanced_prompt[:100]}...")
                print(f"   Reference: Previous image ({visual_assets[index - 1].get('visual_asset_id', 'unknown')})")
                
                # Load the previous image from file (required by the SDK)
                reference_image = Image.open(previous_image_path)
                
                # Create a prompt that emphasizes evolution, not recreation
                consistency_prompt = f"""CRITICAL: This is frame {index + 1} of an animation sequence. 
You MUST keep the EXACT SAME layout, background, colors, and style as the reference image.
The reference image shows the previous frame - evolve it by adding: {enhanced_prompt}
Maintain visual consistency. Do NOT create a completely new image."""
                
                # Pass as multimodal content: [prompt, image]
                response = client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=[consistency_prompt, reference_image],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="16:9",
                        ),
                    ),
                )
                
                # Close the reference image
                reference_image.close()
                
                generated_image = None
                for part in response.parts:
                    if part.inline_data:
                        generated_image = part.as_image()
                        break
                
                if generated_image is None:
                    raise ValueError("No image data returned in response parts.")
                
                generated_image.save(full_filepath)
                previous_image_path = full_filepath
            
            print(f"✅ Saved: {full_filepath.resolve()}")
            results.append({
                "visual_asset_id": asset_id,
                "image_path": str(full_filepath.resolve()),
                "success": True
            })
            
        except Exception as e:
            print(f"❌ Error generating {asset_id}: {e}")
            results.append({
                "visual_asset_id": asset_id,
                "image_path": None,
                "success": False,
                "error": str(e)
            })
            # Don't update previous_image on failure, try to continue with last successful image
    
    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n📊 Generation complete: {successful}/{len(visual_assets)} images generated successfully.")
    
    return results
