"""
Short-Form Video Renderer (9:16 Vertical Format)
Renders videos optimized for TikTok, Instagram Reels, and YouTube Shorts.

Key Features:
- Automatic timestamp generation if missing (no manual intervention needed)
- Unified path management via ProjectManager
- Legacy path compatibility for CLI tools
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lds_mcp.tools.project_manager import get_project_manager, ProjectPaths


# Log file for debugging (always visible)
LOG_FILE = Path(__file__).parent.parent.parent / "data" / "render_log.txt"


def log(message: str, level: str = "INFO"):
    """Log to stderr AND to a file so we can always see what's happening."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}][{level}] {message}"

    # Always print to stderr (Claude Desktop might capture it)
    print(f"[SHORT_RENDERER][{level}] {message}", file=sys.stderr, flush=True)

    # Also write to log file (guaranteed to be visible)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass  # Don't fail if we can't write to log


def clear_log():
    """Clear the log file at the start of a new render."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== Render Log Started at {datetime.now()} ===\n")
    except Exception:
        pass


# Short-form video configuration
SHORT_CONFIG = {
    # Video dimensions (9:16 vertical)
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "background_color": (15, 15, 20),  # Dark background

    # Character positioning for vertical format
    "character_area": {
        "y_start": 0.35,  # Start at 35% from top
        "y_end": 0.85,    # End at 85% from top
        "width_ratio": 0.9  # 90% of screen width
    },

    # Hook text (top of video)
    "hook_text": {
        "y_position": 0.08,  # 8% from top
        "font_size_ratio": 0.035,  # 3.5% of height
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 4,
        "max_width_ratio": 0.85
    },

    # Captions (bottom of video)
    "captions": {
        "y_position": 0.88,  # 88% from top
        "font_size_ratio": 0.04,  # 4% of height
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 6,
        "max_width_ratio": 0.9,
        "shadow_enabled": True
    },

    # Opening image
    "opening_image": {
        "duration": 1.5,  # seconds
        "fade_in": 0.3,
        "fade_out": 0.5
    },

    # Audio
    "narration_volume": 1.0,
    "music_volume": 0.15,  # Lower for shorts

    # Encoding
    "video_codec": "libx264",  # H.264 for compatibility
    "audio_codec": "aac",
    "video_bitrate": "8M",
    "audio_bitrate": "192k",
    "preset": "medium",
    "crf": 23
}

# Pose mapping from new names to existing images
POSE_MAPPING = {
    "sister_faith_close": "analyst_close",
    "sister_faith_front": "analyst_front",
    "sister_faith_pov": "analyst_pov",
    "brother_marcus_close": "skeptic_close",
    "brother_marcus_front": "skeptic_front",
    "brother_marcus_side": "skeptic_side"
}

# Character name mapping for dialogue
CHARACTER_MAPPING = {
    "Sister Faith": "Analyst",
    "Brother Marcus": "Skeptic",
    # Also support reverse mapping
    "Analyst": "Analyst",
    "Skeptic": "Skeptic"
}


async def render_short_video(
    script_id: str,
    hook_text: str,
    opening_image: Optional[str] = None,
    output_filename: str = "short_video",
    shorts_dir: Path = None,
    auto_generate_timestamps: bool = True
) -> dict:
    """
    Render a short-form video (9:16 vertical format).

    Args:
        script_id: ID of the script to render
        hook_text: Text to display at top of video
        opening_image: Optional path to opening/thumbnail image
        output_filename: Output filename without extension
        shorts_dir: Directory for shorts data
        auto_generate_timestamps: If True, automatically generate timestamps if missing

    Returns:
        dict: Render result with output path
    """
    if shorts_dir is None:
        shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"

    shorts_dir = Path(shorts_dir)
    base_dir = shorts_dir.parent.parent

    # Load script
    script_path = shorts_dir / "scripts" / f"{script_id}.json"
    if not script_path.exists():
        return {
            "status": "error",
            "message": f"Script not found: {script_path}",
            "action_required": "Please create a script first using create_script"
        }

    with open(script_path) as f:
        script_data = json.load(f)

    # Check for audio
    audio_path = shorts_dir / "audio" / f"{script_id}.mp3"
    if not audio_path.exists():
        return {
            "status": "error",
            "message": f"Audio not found: {audio_path}",
            "action_required": "Please generate audio first using generate_audio"
        }

    # Check for timestamps - AUTO-GENERATE IF MISSING
    timestamps_path = shorts_dir / "audio" / f"{script_id}_timestamps.json"
    has_timestamps = timestamps_path.exists()

    if not has_timestamps and auto_generate_timestamps:
        # Auto-generate timestamps using Whisper
        print(f"[RENDER] Timestamps missing. Auto-generating from audio...")
        try:
            timestamps_result = await _auto_generate_timestamps(
                audio_path=audio_path,
                timestamps_path=timestamps_path,
                script_data=script_data,
                base_dir=base_dir
            )
            if timestamps_result["status"] == "success":
                has_timestamps = True
                print(f"[RENDER] Timestamps generated successfully: {timestamps_path}")
            else:
                return {
                    "status": "error",
                    "message": f"Failed to auto-generate timestamps: {timestamps_result.get('error', 'Unknown error')}",
                    "details": timestamps_result
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to auto-generate timestamps: {str(e)}",
                "action_required": f"Run manually: python main.py create-dialogue-timestamps --input {audio_path}"
            }

    # Prepare output directory
    output_dir = shorts_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{output_filename}.mp4"

    # Build render plan
    render_plan = {
        "script_id": script_id,
        "config": SHORT_CONFIG,
        "hook_text": hook_text,
        "opening_image": opening_image,
        "audio_file": str(audio_path),
        "timestamps_file": str(timestamps_path) if has_timestamps else None,
        "output_file": str(output_path),
        "pose_mapping": POSE_MAPPING,
        "character_mapping": CHARACTER_MAPPING
    }

    # Final check for timestamps
    if not has_timestamps:
        return {
            "status": "needs_timestamps",
            "message": "Audio timestamps not found and auto-generation failed",
            "render_plan": render_plan,
            "action_required": """
To complete the render, timestamps need to be generated manually:

1. Run the timestamp generation:
   python main.py create-dialogue-timestamps --input {audio_path}

2. Then run render_short again
""",
            "next_steps": [
                "Generate timestamps from audio",
                "Re-run render_short"
            ]
        }

    # If all dependencies are met, provide render instructions
    result = {
        "status": "ready_to_render",
        "render_plan": render_plan,
        "output_path": str(output_path),
        "video_specs": {
            "dimensions": f"{SHORT_CONFIG['width']}x{SHORT_CONFIG['height']}",
            "aspect_ratio": "9:16 (vertical)",
            "format": "MP4 (H.264)",
            "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"]
        },
        "render_command": f"""
To render the video, run:

python -c "
from mcp.tools.short_renderer import execute_render
import asyncio
asyncio.run(execute_render('{script_id}', '{hook_text}', '{opening_image or ''}', '{output_filename}'))
"

Or use the video_handler with short mode:
python main.py video-render --mode short --script {script_id}
""",
        "preview_elements": {
            "hook_text": {
                "text": hook_text,
                "position": "top center",
                "style": "Bold white with black stroke"
            },
            "characters": "Sister Faith & Brother Marcus (animated)",
            "captions": "Auto-generated from dialogue",
            "audio": str(audio_path)
        }
    }

    return result


async def _auto_generate_timestamps(
    audio_path: Path,
    timestamps_path: Path,
    script_data: Dict[str, Any],
    base_dir: Path
) -> Dict[str, Any]:
    """
    Automatically generate timestamps from audio using Whisper.

    This eliminates the need for manual CLI commands.
    """
    try:
        from src.core.whisper import generate_timestamps_from_audio

        # Extract dialogue from script for alignment
        script_content = script_data.get("script", {}).get("dialogue", [])

        if not script_content and isinstance(script_data.get("dialogue"), list):
            script_content = script_data.get("dialogue", [])

        print(f"[TIMESTAMPS] Generating from: {audio_path}")
        print(f"[TIMESTAMPS] Script segments: {len(script_content)}")

        # Generate timestamps
        result_path = generate_timestamps_from_audio(
            audio_file=str(audio_path),
            output_file=str(timestamps_path),
            script_content=script_content,
            model_size="base"
        )

        # Also create legacy copy for CLI compatibility
        legacy_timestamps = base_dir / "data" / "audio" / "elevenlabs" / "dialogue_timestamps.json"
        legacy_timestamps.parent.mkdir(parents=True, exist_ok=True)

        if timestamps_path.exists():
            import shutil
            shutil.copy2(timestamps_path, legacy_timestamps)

        return {
            "status": "success",
            "timestamps_file": str(timestamps_path),
            "legacy_copy": str(legacy_timestamps)
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def execute_render(
    script_id: str,
    hook_text: str,
    opening_image: str = "",
    output_filename: str = "short_video",
    shorts_dir: Path = None
) -> dict:
    """
    Actually execute the video render and create the final MP4 file.

    This function creates a short-form video (9:16 vertical format) using PyAV.
    """
    import traceback

    # Clear log file and start fresh
    clear_log()

    log("=" * 60)
    log("EXECUTE_RENDER STARTED")
    log(f"Log file location: {LOG_FILE}")
    log(f"script_id: {script_id}")
    log(f"hook_text: {hook_text}")
    log(f"opening_image: {opening_image}")
    log(f"output_filename: {output_filename}")
    log("=" * 60)

    # Check dependencies FIRST (fail fast)
    log("Step 0: Checking dependencies...")
    missing_deps = []

    try:
        import av
        log("  PyAV: OK")
    except ImportError as e:
        log(f"  PyAV: MISSING - {e}", "ERROR")
        missing_deps.append(("av", "pip install av"))

    try:
        from PIL import Image
        log("  PIL: OK")
    except ImportError as e:
        log(f"  PIL: MISSING - {e}", "ERROR")
        missing_deps.append(("Pillow", "pip install Pillow"))

    try:
        import numpy
        log("  numpy: OK")
    except ImportError as e:
        log(f"  numpy: MISSING - {e}", "ERROR")
        missing_deps.append(("numpy", "pip install numpy"))

    if missing_deps:
        error_msg = "Missing dependencies:\n"
        for dep, install_cmd in missing_deps:
            error_msg += f"  - {dep}: {install_cmd}\n"
        log(error_msg, "ERROR")
        return {
            "status": "error",
            "message": "Missing required dependencies",
            "missing_dependencies": [d[0] for d in missing_deps],
            "install_commands": [d[1] for d in missing_deps],
            "log_file": str(LOG_FILE)
        }

    log("All dependencies OK")

    if shorts_dir is None:
        shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"

    shorts_dir = Path(shorts_dir)
    base_dir = shorts_dir.parent.parent

    log(f"shorts_dir: {shorts_dir}")
    log(f"base_dir: {base_dir}")

    try:
        # Validate prerequisites
        log("Step 1: Validating prerequisites...")

        script_path = shorts_dir / "scripts" / f"{script_id}.json"
        log(f"Checking script: {script_path}")
        if not script_path.exists():
            log(f"Script NOT FOUND: {script_path}", "ERROR")
            return {
                "status": "error",
                "message": f"Script not found: {script_path}",
                "action_required": "Create a script first using create_script"
            }
        log("Script found OK")

        audio_path = shorts_dir / "audio" / f"{script_id}.mp3"
        log(f"Checking audio: {audio_path}")
        if not audio_path.exists():
            log(f"Audio NOT FOUND: {audio_path}", "ERROR")
            return {
                "status": "error",
                "message": f"Audio not found: {audio_path}",
                "action_required": "Generate audio first using generate_audio"
            }
        log("Audio found OK")

        timestamps_path = shorts_dir / "audio" / f"{script_id}_timestamps.json"
        log(f"Checking timestamps: {timestamps_path}")
        if not timestamps_path.exists():
            log("Timestamps missing. Auto-generating...", "WARN")
            with open(script_path) as f:
                script_data = json.load(f)

            result = await _auto_generate_timestamps(
                audio_path=audio_path,
                timestamps_path=timestamps_path,
                script_data=script_data,
                base_dir=base_dir
            )

            if result["status"] != "success":
                log(f"Failed to generate timestamps: {result}", "ERROR")
                return {
                    "status": "error",
                    "message": f"Failed to generate timestamps: {result.get('error', 'Unknown')}",
                    "details": result
                }
            log("Timestamps generated OK")
        else:
            log("Timestamps found OK")

        # Load data
        log("Step 2: Loading data...")
        with open(script_path) as f:
            script_data = json.load(f)
        log(f"Script loaded: {len(script_data)} keys")

        with open(timestamps_path) as f:
            timestamps_data = json.load(f)
        segments_count = len(timestamps_data.get("segments", []))
        log(f"Timestamps loaded: {segments_count} segments")

        # Prepare output
        log("Step 3: Preparing output...")
        output_dir = shorts_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{output_filename}.mp4"
        log(f"Output path: {output_path}")

        # Create renderer and render video
        log("Step 4: Creating ShortVideoRenderer...")
        renderer = ShortVideoRenderer(
            config=SHORT_CONFIG,
            base_dir=base_dir
        )
        log("Renderer created OK")

        log("Step 5: Starting render...")
        result = renderer.render(
            audio_path=str(audio_path),
            timestamps_data=timestamps_data,
            hook_text=hook_text,
            opening_image=opening_image,
            output_path=str(output_path)
        )
        log(f"Render complete. Status: {result.get('status')}")

        if result["status"] == "success":
            log("=" * 60)
            log("EXECUTE_RENDER COMPLETED SUCCESSFULLY")
            log(f"Output: {output_path}")
            log("=" * 60)
            return {
                "status": "success",
                "output_path": str(output_path),
                "duration": result.get("duration", 0),
                "message": f"Video rendered successfully!",
                "video_specs": {
                    "dimensions": f"{SHORT_CONFIG['width']}x{SHORT_CONFIG['height']}",
                    "format": "MP4 (H.264)",
                    "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"]
                }
            }
        else:
            log(f"Render failed: {result}", "ERROR")
            return result

    except Exception as e:
        error_tb = traceback.format_exc()
        log(f"EXCEPTION: {str(e)}", "ERROR")
        log(f"Traceback:\n{error_tb}", "ERROR")
        return {
            "status": "error",
            "message": str(e),
            "traceback": error_tb
        }


class ShortVideoRenderer:
    """
    Renderer for short-form videos (9:16 vertical format).
    Uses PyAV for efficient video encoding.
    """

    def __init__(self, config: dict, base_dir: Path):
        log("ShortVideoRenderer.__init__ starting...")
        self.config = config
        self.base_dir = Path(base_dir)
        self.width = config["width"]
        self.height = config["height"]
        self.fps = config["fps"]
        self.bg_color = config["background_color"]

        log(f"Video config: {self.width}x{self.height} @ {self.fps}fps")

        # Font setup
        self.font_path = self.base_dir / "data" / "font" / "GoogleSans-SemiBold.ttf"
        self._font_cache = {}
        log(f"Font path: {self.font_path} (exists: {self.font_path.exists()})")

        # Character images directory
        self.images_dir = self.base_dir / "data" / "images"
        log(f"Images dir: {self.images_dir} (exists: {self.images_dir.exists()})")
        log("ShortVideoRenderer.__init__ complete")

    def _get_font(self, size: int):
        """Get or create a font of the specified size."""
        from PIL import ImageFont

        if size not in self._font_cache:
            try:
                self._font_cache[size] = ImageFont.truetype(str(self.font_path), size)
                log(f"Font loaded: size {size}")
            except IOError as e:
                log(f"Could not load font: {e}. Using default", "WARN")
                self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def _load_character_image(self, character: str, pose: str = "front", mouth_open: bool = True) -> Optional[any]:
        """Load a character image based on character name and pose.

        Args:
            character: Character name (Analyst, Skeptic, etc.)
            pose: Pose type (close, front, side, pov)
            mouth_open: Whether to load open mouth (True) or closed mouth (False) image
        """
        from PIL import Image

        # Map character names
        char_key = CHARACTER_MAPPING.get(character, character)
        char_lower = char_key.lower()

        # Map pose to directory name
        pose_to_dir = {
            "close": "close_view",
            "front": "front_view",
            "side": "side_view",
            "pov": "pov_view"
        }

        pose_dir = pose_to_dir.get(pose, f"{pose}_view")
        mouth_state = "Open" if mouth_open else "Closed"

        # Build possible paths based on actual directory structure
        # Structure: data/images/{character}/{pose}_view/{Pose}Mouth_{State}.png
        possible_paths = [
            # New structure: analyst/close_view/CloseMouth_Open.png
            self.images_dir / char_lower / pose_dir / f"CloseMouth_{mouth_state}.png",
            self.images_dir / char_lower / pose_dir / f"FrontMouth_{mouth_state}.png",
            self.images_dir / char_lower / pose_dir / f"SideMouth_{mouth_state}.png",
            self.images_dir / char_lower / pose_dir / f"PovMouth_{mouth_state}.png",
            # Generic pattern
            self.images_dir / char_lower / pose_dir / f"{pose.capitalize()}Mouth_{mouth_state}.png",
            # Fallback to old flat structure
            self.images_dir / f"{char_lower}_{pose}.png",
            self.images_dir / f"{char_lower}.png",
        ]

        log(f"Looking for image: {character} -> {char_lower}/{pose_dir} (mouth: {mouth_state})")
        for img_path in possible_paths:
            log(f"  Trying: {img_path} (exists: {img_path.exists()})")
            if img_path.exists():
                try:
                    img = Image.open(img_path).convert("RGBA")
                    log(f"  Loaded: {img_path} ({img.size})")
                    return img
                except Exception as e:
                    log(f"  Error loading {img_path}: {e}", "ERROR")

        log(f"  No image found for {character}", "WARN")
        return None

    def _create_frame(
        self,
        character: str,
        caption_text: str,
        hook_text: str,
        character_image: any = None
    ) -> any:
        """Create a single video frame."""
        from PIL import Image, ImageDraw
        import numpy as np

        # Create base frame with background color
        frame = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(frame)

        # 1. Draw character image (centered in character area)
        if character_image:
            char_cfg = self.config["character_area"]
            char_y_start = int(self.height * char_cfg["y_start"])
            char_y_end = int(self.height * char_cfg["y_end"])
            char_width = int(self.width * char_cfg["width_ratio"])
            char_height = char_y_end - char_y_start

            # Resize character to fit
            img_ratio = character_image.width / character_image.height
            target_ratio = char_width / char_height

            if img_ratio > target_ratio:
                new_width = char_width
                new_height = int(char_width / img_ratio)
            else:
                new_height = char_height
                new_width = int(char_height * img_ratio)

            resized = character_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Center in character area
            x = (self.width - new_width) // 2
            y = char_y_start + (char_height - new_height) // 2

            # Paste with alpha if available
            if resized.mode == 'RGBA':
                frame.paste(resized, (x, y), resized)
            else:
                frame.paste(resized, (x, y))

        # 2. Draw hook text at top
        if hook_text:
            hook_cfg = self.config["hook_text"]
            font_size = int(self.height * hook_cfg["font_size_ratio"])
            font = self._get_font(font_size)

            y_pos = int(self.height * hook_cfg["y_position"])

            # Draw with stroke for visibility
            self._draw_text_with_stroke(
                draw, hook_text, font,
                x=self.width // 2,
                y=y_pos,
                text_color=tuple(hook_cfg["color"]),
                stroke_color=tuple(hook_cfg["stroke_color"]),
                stroke_width=hook_cfg["stroke_width"],
                anchor="mt"  # Middle-Top
            )

        # 3. Draw caption at bottom
        if caption_text:
            cap_cfg = self.config["captions"]
            font_size = int(self.height * cap_cfg["font_size_ratio"])
            font = self._get_font(font_size)

            y_pos = int(self.height * cap_cfg["y_position"])

            # Draw with stroke
            self._draw_text_with_stroke(
                draw, caption_text, font,
                x=self.width // 2,
                y=y_pos,
                text_color=tuple(cap_cfg["color"]),
                stroke_color=tuple(cap_cfg["stroke_color"]),
                stroke_width=cap_cfg["stroke_width"],
                anchor="mm"  # Middle-Middle
            )

        return np.array(frame)

    def _draw_text_with_stroke(
        self, draw, text: str, font, x: int, y: int,
        text_color: tuple, stroke_color: tuple, stroke_width: int,
        anchor: str = "mm"
    ):
        """Draw text with stroke/outline for better visibility."""
        # Draw stroke (outline)
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx * dx + dy * dy <= stroke_width * stroke_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color, anchor=anchor)

        # Draw main text
        draw.text((x, y), text, font=font, fill=text_color, anchor=anchor)

    def render(
        self,
        audio_path: str,
        timestamps_data: dict,
        hook_text: str,
        opening_image: str,
        output_path: str
    ) -> dict:
        """
        Render the complete video.
        """
        log("=" * 50)
        log("ShortVideoRenderer.render() STARTING")
        log(f"audio_path: {audio_path}")
        log(f"hook_text: {hook_text}")
        log(f"output_path: {output_path}")
        log("=" * 50)

        try:
            log("Importing av (PyAV)...")
            import av
            log("PyAV imported OK")
        except ImportError as e:
            log(f"FAILED to import PyAV: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"PyAV not installed: {e}",
                "fix": "pip install av"
            }

        try:
            from PIL import Image
            import numpy as np
            log("PIL and numpy imported OK")
        except ImportError as e:
            log(f"FAILED to import PIL/numpy: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"Missing dependency: {e}"
            }

        try:
            # Get audio duration
            log(f"Opening audio file: {audio_path}")
            audio_container = av.open(audio_path)
            audio_stream = audio_container.streams.audio[0]
            audio_duration = float(audio_container.duration) / av.time_base
            audio_container.close()
            log(f"Audio duration: {audio_duration:.2f}s")

            # Prepare segments timeline
            segments = timestamps_data.get("segments", [])
            log(f"Segments in timestamps: {len(segments)}")

            # Build captions timeline from words
            captions_timeline = []
            total_words = 0
            for segment in segments:
                for word in segment.get("words", []):
                    text = word.get("text", word.get("word", "")).strip()
                    if text and word.get("start") is not None:
                        captions_timeline.append({
                            "start": word["start"],
                            "end": word["end"],
                            "text": text,
                            "character": segment.get("character", "")
                        })
                        total_words += 1
            log(f"Captions timeline built: {total_words} words")

            # Load character images (both open and closed mouth for animation)
            log("Loading character images...")
            character_images = {}
            for char in ["Analyst", "Skeptic"]:
                # Load both mouth states for each character
                img_open = self._load_character_image(char, "close", mouth_open=True)
                img_closed = self._load_character_image(char, "close", mouth_open=False)

                if img_open or img_closed:
                    character_images[char] = {
                        "open": img_open or img_closed,  # Fallback if one is missing
                        "closed": img_closed or img_open
                    }
                    log(f"Loaded images for {char}: open={img_open is not None}, closed={img_closed is not None}")
                else:
                    log(f"No images found for {char}", "WARN")

            # Create output container
            log(f"Creating output container: {output_path}")
            output_container = av.open(output_path, mode='w')

            # Add video stream
            log("Adding video stream...")
            video_stream = output_container.add_stream(
                self.config["video_codec"],
                rate=self.fps
            )
            video_stream.width = self.width
            video_stream.height = self.height
            video_stream.pix_fmt = 'yuv420p'
            video_stream.bit_rate = int(self.config["video_bitrate"].replace("M", "000000"))
            log(f"Video stream: {self.width}x{self.height}, {self.config['video_codec']}")

            # Render frames
            total_frames = int(audio_duration * self.fps)
            log(f"Starting frame render: {total_frames} frames")

            current_character = "Analyst"

            for frame_idx in range(total_frames):
                current_time = frame_idx / self.fps

                # Find active caption and character
                active_caption = ""
                is_speaking = False
                word_progress = 0.0
                for cap in captions_timeline:
                    if cap["start"] <= current_time <= cap["end"]:
                        active_caption = cap["text"]
                        is_speaking = True
                        # Calculate progress within the word for mouth animation
                        word_duration = cap["end"] - cap["start"]
                        if word_duration > 0:
                            word_progress = (current_time - cap["start"]) / word_duration
                        if cap["character"]:
                            mapped_char = CHARACTER_MAPPING.get(cap["character"], cap["character"])
                            current_character = mapped_char
                        break

                # Get character image with mouth animation
                char_data = character_images.get(current_character)
                char_img = None
                if char_data:
                    if is_speaking:
                        # Alternate mouth open/closed based on time (syllable-like animation)
                        # Open mouth for first 50% of each syllable cycle (approx 100ms cycles)
                        cycle_position = (current_time * 10) % 1.0  # 10 cycles per second
                        mouth_open = cycle_position < 0.5
                        char_img = char_data["open"] if mouth_open else char_data["closed"]
                    else:
                        # Not speaking - mouth closed
                        char_img = char_data["closed"]

                # Create frame
                frame_array = self._create_frame(
                    character=current_character,
                    caption_text=active_caption,
                    hook_text=hook_text,
                    character_image=char_img
                )

                # Encode frame
                frame = av.VideoFrame.from_ndarray(frame_array, format='rgb24')
                frame.pts = frame_idx

                for packet in video_stream.encode(frame):
                    output_container.mux(packet)

                # Progress indicator every 10 seconds
                if frame_idx % (self.fps * 10) == 0:
                    progress = (frame_idx / total_frames) * 100
                    log(f"Render progress: {progress:.1f}% ({frame_idx}/{total_frames})")

            log("Flushing video encoder...")
            # Flush video encoder
            for packet in video_stream.encode():
                output_container.mux(packet)

            output_container.close()
            log("Video container closed")

            # Now mux audio with video using ffmpeg
            log("Adding audio track with FFmpeg...")
            temp_output = output_path.replace(".mp4", "_temp.mp4")
            os.rename(output_path, temp_output)

            import subprocess
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", temp_output,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", self.config["audio_bitrate"],
                "-shortest",
                output_path
            ]
            log(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                log(f"FFmpeg FAILED: {result.stderr}", "ERROR")
                # Fallback: keep video without audio
                os.rename(temp_output, output_path)
                return {
                    "status": "partial",
                    "message": "Video created but audio muxing failed",
                    "output_path": output_path,
                    "error": result.stderr
                }

            # Clean up temp file
            if os.path.exists(temp_output):
                os.remove(temp_output)
                log("Temp file cleaned up")

            log("=" * 50)
            log(f"RENDER COMPLETE: {output_path}")
            log("=" * 50)

            return {
                "status": "success",
                "output_path": output_path,
                "duration": audio_duration,
                "frames": total_frames
            }

        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            log(f"RENDER EXCEPTION: {str(e)}", "ERROR")
            log(f"Traceback:\n{error_tb}", "ERROR")
            return {
                "status": "error",
                "message": str(e),
                "traceback": error_tb
            }


def create_short_video_script(
    script_data: dict,
    timestamps_data: dict,
    hook_text: str,
    opening_image: Optional[str] = None
) -> dict:
    """
    Create a video script formatted for the short renderer.

    Args:
        script_data: The dialogue script
        timestamps_data: Word-level timestamps from Whisper
        hook_text: Text overlay for top of video
        opening_image: Optional opening image path

    Returns:
        dict: Video script ready for rendering
    """
    video_script = {
        "format": "short",
        "dimensions": {
            "width": SHORT_CONFIG["width"],
            "height": SHORT_CONFIG["height"]
        },
        "hook_text": hook_text,
        "opening_image": opening_image,
        "segments": []
    }

    # Process each segment from timestamps
    for segment in timestamps_data.get("segments", []):
        char = segment.get("character", "")

        # Map character name
        mapped_char = CHARACTER_MAPPING.get(char, char)

        video_segment = {
            "character": mapped_char,
            "text": segment.get("text", ""),
            "start": segment.get("start", 0),
            "end": segment.get("end", 0),
            "words": segment.get("words", []),
            "pose_id": None  # Will be filled from script
        }

        video_script["segments"].append(video_segment)

    return video_script
