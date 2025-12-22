import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from utils.captionGenerator import CaptionGenerator
from PIL import Image

def test_long_shadow():
    # Mock video plan
    video_plan = [
        {
            "words": [
                {"text": "LONG SHADOW TEST", "start": 0.0, "end": 2.0}
            ]
        }
    ]
    
    width = 1920
    height = 1080
    
    # Initialize generator
    # It will find the font automatically in data/font/GoogleSans-SemiBold.ttf
    generator = CaptionGenerator(video_plan, width, height)
    
    # Get image at t=1.0
    img = generator.get_caption_image(1.0)
    
    if img:
        output_path = os.path.join(os.path.dirname(__file__), "long_shadow_result.png")
        img.save(output_path)
        print(f"Success! Image saved to {output_path}")
    else:
        print("Failed to generate image.")

if __name__ == "__main__":
    test_long_shadow()
