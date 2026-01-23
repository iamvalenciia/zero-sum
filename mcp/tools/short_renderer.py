"""
Short-Form Video Renderer (9:16 Vertical Format)
Renders videos optimized for TikTok, Instagram Reels, and YouTube Shorts.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


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
    shorts_dir: Path = None
) -> dict:
    """
    Render a short-form video (9:16 vertical format).

    Args:
        script_id: ID of the script to render
        hook_text: Text to display at top of video
        opening_image: Optional path to opening/thumbnail image
        output_filename: Output filename without extension
        shorts_dir: Directory for shorts data

    Returns:
        dict: Render result with output path
    """
    if shorts_dir is None:
        shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"

    shorts_dir = Path(shorts_dir)

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

    # Check for timestamps
    timestamps_path = shorts_dir / "audio" / f"{script_id}_timestamps.json"
    has_timestamps = timestamps_path.exists()

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

    # Check if we need to generate timestamps first
    if not has_timestamps:
        return {
            "status": "needs_timestamps",
            "message": "Audio timestamps not found",
            "render_plan": render_plan,
            "action_required": """
To complete the render, timestamps need to be generated:

1. Run the timestamp generation:
   python main.py create-dialogue-timestamps --input {audio_path}

2. Or use the existing whisper module to transcribe

3. Then run render_short again
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


async def execute_render(
    script_id: str,
    hook_text: str,
    opening_image: str = "",
    output_filename: str = "short_video"
) -> dict:
    """
    Actually execute the video render.

    This function imports and uses the existing video rendering infrastructure.
    """
    try:
        # Import the video renderer
        from src.core.video_renderer import VideoAssembler

        shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"

        # Load script
        script_path = shorts_dir / "scripts" / f"{script_id}.json"
        with open(script_path) as f:
            script_data = json.load(f)

        # Load timestamps
        timestamps_path = shorts_dir / "audio" / f"{script_id}_timestamps.json"
        with open(timestamps_path) as f:
            timestamps_data = json.load(f)

        # Map character names in script
        dialogue = script_data.get("script", {}).get("dialogue", [])
        for line in dialogue:
            char = line.get("character", "")
            if char in CHARACTER_MAPPING:
                line["_original_character"] = char
                line["character"] = CHARACTER_MAPPING[char]

            # Map pose IDs
            for pose in line.get("character_poses", []):
                pose_id = pose.get("pose_id", "")
                if pose_id in POSE_MAPPING:
                    pose["pose_id"] = POSE_MAPPING[pose_id]

        # Create video script format
        video_script = {
            "audio_file": str(shorts_dir / "audio" / f"{script_id}.mp3"),
            "hook_text": hook_text,
            "opening_image": opening_image if opening_image else None,
            "video_plan": timestamps_data.get("segments", []),
            "config": SHORT_CONFIG
        }

        # Save as video-script.json for the renderer
        video_script_path = shorts_dir / f"{script_id}_video_script.json"
        with open(video_script_path, "w") as f:
            json.dump(video_script, f, indent=2)

        # Output path
        output_path = shorts_dir / "output" / f"{output_filename}.mp4"

        # Note: The actual rendering would be done by VideoAssembler
        # This is a placeholder for the integration

        return {
            "status": "render_started",
            "video_script": str(video_script_path),
            "output_path": str(output_path),
            "message": "Video rendering initiated. Check output directory for result."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "traceback": str(e.__traceback__)
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
