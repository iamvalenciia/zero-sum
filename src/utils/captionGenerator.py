from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Optional, Tuple
import os

class CaptionGenerator:
    """
    Handles the generation of caption overlays for the video.
    Renders bright white text on a translucent background bar.
    """
    
    def __init__(self, video_plan: List[Dict], width: int, height: int, font_path: str = None, 
                 font_size: int = None, bottom_margin: int = None, text_color: Tuple = None):
        self.video_plan = video_plan
        self.width = width
        self.height = height
        
        # Resolve font path
        if font_path is None:
             # Assuming running from project root, or try to find it relative to this file
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             self.font_path = os.path.join(base_dir, "data", "font", "GoogleSans-SemiBold.ttf")
        else:
            self.font_path = font_path
        
        # Configuration
        self.text_color = text_color if text_color else (255, 255, 255, 255)   # Default: White
        self.bg_color = None                                                  # No background
        self.stroke_color = (0, 0, 0, 255)                                    # Black stroke
        self.stroke_width = 10                                                # Thick outline for 4K
        
        # Long Shadow Configuration
        self.shadow_color = (0, 0, 0, 255)                                    # Black shadow
        self.shadow_length = 10                                               # How many steps for the shadow
        self.shadow_offset_step = 2                                          # Pixels per step (diagonal)
        
        # Font Size
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = int(height * 0.085)    # Increased visibility: 8.5% of video height

        # Bottom Margin
        if bottom_margin is not None:
            self.bottom_margin = bottom_margin
        else:
            self.bottom_margin = int(height * 0.08) # Default: 8% (Anime standard position)
        
        # Pre-load font
        try:
            self.font = ImageFont.truetype(self.font_path, self.font_size)
        except IOError:
            print(f"Warning: Could not load font '{self.font_path}'. Using default.")
            self.font = ImageFont.load_default()
        
        # Cache for generated caption images (key: text, value: PIL Image)
        self._caption_cache = {}
        self._current_caption_text = None
        self._current_caption_image = None
            
        # Prepare timeline
        self.captions_timeline = self._prepare_captions_timeline()

    def _prepare_captions_timeline(self) -> List[Dict]:
        """
        Flattens the video plan into a list of caption events.
        Each event has: start, end, text
        """
        captions = []
        for segment in self.video_plan:
            for word_data in segment.get("words", []):
                # Try 'text' first (correct key), fallback to 'word' (legacy/test)
                text = word_data.get("text", word_data.get("word", "")).strip()
                start = word_data.get("start")
                end = word_data.get("end")
                
                if text and start is not None and end is not None:
                    captions.append({
                        "start": start,
                        "end": end,
                        "text": text
                    })

        # Sort by start time
        captions.sort(key=lambda x: x["start"])
        return captions

    def get_caption_image(self, time: float) -> Optional[Image.Image]:
        """
        Returns a transparent PIL Image with the caption for the given time,
        or None if no caption should be displayed.
        Uses caching to avoid regenerating images for the same caption text.
        """
        # Find active caption
        active_caption = None
        for cap in self.captions_timeline:
            if cap["start"] <= time <= cap["end"]:
                active_caption = cap
                break
            if cap["start"] > time:
                # Since list is sorted, we can stop early
                break
                
        if not active_caption:
            return None
            
        text = active_caption["text"]
        
        # Check cache - return cached image if same text
        if text == self._current_caption_text and self._current_caption_image is not None:
            return self._current_caption_image
        
        # Check persistent cache
        if text in self._caption_cache:
            self._current_caption_text = text
            self._current_caption_image = self._caption_cache[text]
            return self._current_caption_image
        
        # Create a transparent overlay
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Calculate positions using anchor 'mm' (Middle Middle) for box centering
        # But to prevent jumping baselines, we use 'mb' (Middle Baseline)
        
        # Center horizontally
        x = self.width // 2
        # Position at bottom with margin (this is the baseline position)
        y = self.height - self.bottom_margin
        
        # 1. Draw Long Shadow
        # We iterate to create a "trailing" shadow effect
        for i in range(1, self.shadow_length + 1):
            offset = i * self.shadow_offset_step
            # Draw the shadow text with a small offset each time
            # Moving it slightly down and to the right
            draw.text(
                (x + offset, y + offset), 
                text, 
                font=self.font, 
                fill=self.shadow_color, 
                anchor='mb'
            )

        # 2. Draw Text with Stroke (Main Layer)
        draw.text(
            (x, y), 
            text, 
            font=self.font, 
            fill=self.text_color, 
            anchor='mb',
            stroke_width=self.stroke_width,
            stroke_fill=self.stroke_color
        )
        
        # Cache the result
        self._caption_cache[text] = overlay
        self._current_caption_text = text
        self._current_caption_image = overlay
        
        return overlay
