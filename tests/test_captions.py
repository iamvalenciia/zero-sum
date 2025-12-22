import os
import sys
from PIL import Image
import numpy as np

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.captionGenerator import CaptionGenerator

def test_caption_rendering():
    print("Testing caption rendering...")
    
    # Sample video plan
    video_plan = [
        {
            "words": [
                {"text": "Esto es una prueba", "start": 0.0, "end": 2.0},
                {"text": "de subtitulos estilo anime", "start": 2.1, "end": 4.0}
            ]
        }
    ]
    
    width, height = 1920, 1080
    
    # Initialize generator
    # We use a standard font path if possible, or let it fallback
    gen = CaptionGenerator(video_plan, width, height)
    
    # Create a gray background image to see white text and black outline
    bg = Image.new('RGB', (width, height), (128, 128, 128))
    
    # Get caption at t=1.0
    cap_img = gen.get_caption_image(1.0)
    
    if cap_img:
        bg.paste(cap_img, (0, 0), cap_img)
        
        # Save result
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "tests")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "caption_preview.png")
        bg.save(output_path)
        print(f"Preview saved to: {output_path}")
    else:
        print("Failed to generate caption image.")

if __name__ == "__main__":
    test_caption_rendering()
