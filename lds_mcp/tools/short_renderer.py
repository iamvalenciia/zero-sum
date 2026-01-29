"""
Short-Form Video Renderer (9:16 Vertical Format)
Renders videos optimized for TikTok, Instagram Reels, and YouTube Shorts.

Key Features:
- Automatic timestamp generation if missing (no manual intervention needed)
- Unified path management via ProjectManager
- Legacy path compatibility for CLI tools
- Lip-sync support using images_catalog.json (open/closed mouth)
- Pose-based character switching from script
- Standardized image loading via ImageLoader
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lds_mcp.tools.project_manager import get_project_manager, ProjectPaths
from lds_mcp.tools.image_loader import (
    ImageLoader,
    get_image_loader,
    CHARACTER_ALIASES,
    STANDARD_CHARACTERS,
    STANDARD_POSES,
    get_pose_for_emotion
)


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


# Status file for tracking render progress
STATUS_FILE = Path(__file__).parent.parent.parent / "data" / "shorts" / "render_status.json"


def update_render_status(phase: str, message: str, progress: float = 0, extra: dict = None):
    """Update the render status file for real-time progress tracking."""
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        status = {
            "phase": phase,
            "message": message,
            "progress": round(progress, 1),
            "last_updated": datetime.now().isoformat(),
        }
        if extra:
            status.update(extra)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
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
        "font_size_ratio": 0.035,  # 3.5% of height (reduced by half)
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 4,  # Reduced stroke for smaller text
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

    # Floating images (visual assets / illustrations)
    "floating_images": {
        "enabled": True,
        "min_interval_seconds": 15,    # Minimum seconds between images
        "max_interval_seconds": 20,    # Maximum seconds between images
        "display_duration": 5,         # How long each image shows (seconds)
        "fade_in": 0.5,                # Fade in duration
        "fade_out": 0.5,               # Fade out duration
        "size_ratio": 0.6,             # Image size relative to screen width
        "y_position": 0.45,            # Center position (45% from top)
        "background_blur": 15,         # Blur radius for character behind
        "skip_first_seconds": 5,       # Don't show images in first N seconds
        "skip_last_seconds": 5,        # Don't show images in last N seconds
        "hide_captions": True          # Hide captions when showing floating image
    },

    # Audio
    "narration_volume": 1.0,
    "music_volume": 0.12,  # Background music volume (ambient, not distracting)
    "music_path": "data/audio/music/Frolic-Es-Jammy-Jams.mp3",  # Nature/piano ambient music
    "normalize_music": True,  # Normalize music volume for consistent levels

    # Encoding - GPU acceleration
    "gpu_encoding": {
        "enabled": True,               # Try GPU encoding first
        "nvidia_codec": "h264_nvenc",  # NVIDIA NVENC encoder
        "nvidia_preset": "p4",         # Balance of speed/quality (p1=fastest, p7=best)
        "nvidia_tune": "hq",           # High quality tuning
        "fallback_to_cpu": True        # Fall back to libx264 if GPU fails
    },
    "video_codec": "libx264",  # CPU fallback
    "audio_codec": "aac",
    "video_bitrate": "8M",
    "audio_bitrate": "192k",
    "preset": "medium",
    "crf": 23,

    # Lip sync - improved syllable-based animation (anime-style)
    "lip_sync": {
        "enabled": True,
        "mode": "syllable",            # "syllable" for natural, "fast" for old behavior
        "syllable_duration_ms": 80,    # Duration of each syllable cycle (ms) - faster for natural speech
        "open_ratio": 0.55,            # Mouth open for 55% of syllable (slightly faster close)
        "min_syllable_ms": 60,         # Minimum syllable duration (prevents too fast)
        "max_syllable_ms": 120,        # Maximum syllable duration (prevents too slow)
        "pause_threshold_ms": 150,     # Pause longer than this = mouth closed
        "vowels": "aeiouáéíóúAEIOUÁÉÍÓÚ",  # Characters that trigger mouth open
        "respect_punctuation": True,   # Close mouth on . , ; : ! ?
        "transition_frames": 1         # Frames for smooth transition (reduced for snappier animation)
    }
}

# Character name mapping for dialogue (for backward compatibility)
CHARACTER_MAPPING = {
    "Sister Faith": "Analyst",
    "Brother Marcus": "Skeptic",
    "Analyst": "Analyst",
    "Skeptic": "Skeptic",
    "analyst": "Analyst",
    "skeptic": "Skeptic"
}


@dataclass
class WordTiming:
    """Represents a word with its timing and associated character/pose."""
    word: str
    start: float
    end: float
    character: str
    pose_id: str


@dataclass
class RenderSegment:
    """A segment of video to render with specific character and pose."""
    character: str
    pose_id: str
    start_time: float
    end_time: float
    words: List[WordTiming]


def build_render_timeline(
    timestamps_data: Dict[str, Any],
    script_data: Dict[str, Any]
) -> List[RenderSegment]:
    """
    Build a timeline of render segments from timestamps and script data.

    This merges timestamp data (word timings) with script data (pose assignments)
    to create a complete render plan.
    """
    segments = []

    # Extract dialogue from script
    dialogue = script_data.get("script", {}).get("dialogue", [])
    if not dialogue and isinstance(script_data.get("dialogue"), list):
        dialogue = script_data.get("dialogue", [])

    # Build a map of dialogue lines with their poses
    dialogue_poses = []
    for line in dialogue:
        character = line.get("character", "Analyst")
        character = CHARACTER_MAPPING.get(character, character)

        poses = line.get("character_poses", [])
        if not poses:
            # Default pose based on character
            char_key = CHARACTER_ALIASES.get(character, character.lower())
            default_pose = STANDARD_CHARACTERS.get(char_key, STANDARD_CHARACTERS["analyst"]).default_pose
            poses = [{"pose_id": default_pose, "start_word_index": 0, "end_word_index": 999}]

        dialogue_poses.append({
            "character": character,
            "poses": poses,
            "text": line.get("text", "")
        })

    # Process timestamp segments
    timestamp_segments = timestamps_data.get("segments", [])

    for seg_idx, segment in enumerate(timestamp_segments):
        character = segment.get("character", "Analyst")
        character = CHARACTER_MAPPING.get(character, character)

        # Get pose info from dialogue if available
        pose_info = None
        if seg_idx < len(dialogue_poses):
            pose_info = dialogue_poses[seg_idx]
            character = pose_info["character"]  # Use character from script

        words = segment.get("words", [])
        if not words:
            continue

        # Build word timings with pose assignments
        word_timings = []
        for word_idx, word in enumerate(words):
            word_text = word.get("text", word.get("word", "")).strip()
            if not word_text:
                continue

            # Determine pose for this word
            pose_id = None
            if pose_info:
                for pose in pose_info["poses"]:
                    start_idx = pose.get("start_word_index", 0)
                    end_idx = pose.get("end_word_index", 999)
                    if start_idx <= word_idx <= end_idx:
                        pose_id = pose.get("pose_id")
                        break

            if not pose_id:
                # Default pose
                char_key = CHARACTER_ALIASES.get(character, character.lower())
                pose_id = STANDARD_CHARACTERS.get(char_key, STANDARD_CHARACTERS["analyst"]).default_pose

            word_timings.append(WordTiming(
                word=word_text,
                start=word.get("start", 0),
                end=word.get("end", 0),
                character=character,
                pose_id=pose_id
            ))

        if word_timings:
            # Group consecutive words with same character/pose into segments
            current_segment = None
            for wt in word_timings:
                if current_segment is None or current_segment.character != wt.character or current_segment.pose_id != wt.pose_id:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = RenderSegment(
                        character=wt.character,
                        pose_id=wt.pose_id,
                        start_time=wt.start,
                        end_time=wt.end,
                        words=[wt]
                    )
                else:
                    current_segment.end_time = wt.end
                    current_segment.words.append(wt)

            if current_segment:
                segments.append(current_segment)

    return segments


def validate_render_prerequisites(
    script_id: str,
    shorts_dir: Path = None,
    base_dir: Path = None
) -> Dict[str, Any]:
    """
    Validate all render prerequisites BEFORE starting the render.

    This function checks:
    1. Character images exist (with correct extensions)
    2. Visual assets/floating images can be found
    3. Script structure is valid
    4. Audio and timestamps exist

    Returns a detailed validation report with errors and warnings.
    Call this BEFORE render_short_video to avoid wasted render time.
    """
    import re

    if shorts_dir is None:
        shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent

    shorts_dir = Path(shorts_dir)
    base_dir = Path(base_dir)

    errors = []
    warnings = []
    info = []

    # 1. Check script exists
    script_path = shorts_dir / "scripts" / f"{script_id}.json"
    if not script_path.exists():
        errors.append(f"Script not found: {script_path}")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "summary": "Script file not found. Cannot proceed."
        }

    with open(script_path) as f:
        script_data = json.load(f)
    info.append(f"Script loaded: {script_id}")

    # 2. Check audio file
    audio_path = shorts_dir / "audio" / f"{script_id}.mp3"
    if not audio_path.exists():
        errors.append(f"Audio file not found: {audio_path}")
    else:
        info.append(f"Audio file found: {audio_path.name}")

    # 3. Check timestamps file
    timestamps_path = shorts_dir / "audio" / f"{script_id}_timestamps.json"
    if not timestamps_path.exists():
        warnings.append(f"Timestamps file not found: {timestamps_path.name} (will be auto-generated)")
    else:
        info.append(f"Timestamps file found: {timestamps_path.name}")

    # 4. Check CHARACTER IMAGES (the main issue!)
    images_dir = base_dir / "data" / "images"
    extensions = [".png", ".jpeg", ".jpg", ".webp"]

    # Get dialogue to determine which characters are used
    dialogue = script_data.get("dialogue", [])
    characters_used = set()
    for line in dialogue:
        char = line.get("character", "")
        mapped_char = CHARACTER_MAPPING.get(char, char)
        characters_used.add(mapped_char)

    info.append(f"Characters in script: {list(characters_used)}")

    for character in characters_used:
        char_lower = character.lower()
        char_dir = images_dir / char_lower

        if not char_dir.exists():
            errors.append(f"Character directory not found: {char_dir}")
            continue

        # Check for close_view (most commonly used)
        pose_dirs = ["close_view", "front_view", "side_view", "pov_view"]
        found_poses = []

        for pose_dir in pose_dirs:
            pose_path = char_dir / pose_dir
            if pose_path.exists():
                # Check for mouth images
                mouth_open_found = False
                mouth_closed_found = False

                for ext in extensions:
                    # Check various naming patterns
                    patterns = [
                        f"CloseMouth_Open{ext}",
                        f"FrontMouth_Open{ext}",
                        f"SideMouth_Open{ext}",
                        f"PovMouth_Open{ext}",
                    ]
                    for pattern in patterns:
                        if (pose_path / pattern).exists():
                            mouth_open_found = True
                            break

                    patterns_closed = [
                        f"CloseMouth_Closed{ext}",
                        f"FrontMouth_Closed{ext}",
                        f"SideMouth_Closed{ext}",
                        f"PovMouth_Closed{ext}",
                        f"FrontMouth_Close{ext}",  # Handle typo in skeptic
                    ]
                    for pattern in patterns_closed:
                        if (pose_path / pattern).exists():
                            mouth_closed_found = True
                            break

                if mouth_open_found and mouth_closed_found:
                    found_poses.append(pose_dir)
                elif mouth_open_found or mouth_closed_found:
                    warnings.append(f"{character}/{pose_dir}: Missing {'open' if not mouth_open_found else 'closed'} mouth image")
                    found_poses.append(f"{pose_dir} (partial)")

        if found_poses:
            info.append(f"{character}: Found poses - {', '.join(found_poses)}")
        else:
            errors.append(f"{character}: No valid pose images found! Check {char_dir}")

    # 5. Check FLOATING IMAGES / Visual Assets
    visual_assets_dir = shorts_dir / "images"
    visual_assets_in_script = []

    for line in dialogue:
        line_assets = line.get("visual_assets") or []
        for va in line_assets:
            visual_id = va.get("visual_asset_id", "")
            if visual_id:
                visual_assets_in_script.append(visual_id)

    if visual_assets_in_script:
        info.append(f"Visual assets in script: {visual_assets_in_script}")

        # Check image registry
        registry_path = shorts_dir / "images" / "image_registry.json"
        if registry_path.exists():
            info.append("Image registry found")
        else:
            warnings.append("image_registry.json not found - will use naming convention")

        # Check if images exist
        available_images = []
        for ext in [".jpeg", ".jpg", ".png", ".webp"]:
            available_images.extend(visual_assets_dir.glob(f"*{ext}"))

        image_names = [f.stem for f in available_images]
        info.append(f"Available images in shorts/images: {[f.name for f in available_images]}")

        # Try to match visual assets to images
        for visual_id in visual_assets_in_script:
            # Extract number from visual_id (e.g., "1a" -> 1)
            match = re.match(r"(\d+)", visual_id)
            target_num = match.group(1) if match else None

            found = False
            # Check exact match
            if visual_id in image_names:
                found = True
            # Check numeric match (e.g., "1a" matches "1")
            elif target_num and target_num in image_names:
                found = True
            # Check by index
            elif target_num:
                numeric_images = [f for f in available_images if re.match(r"^\d+$", f.stem)]
                if len(numeric_images) >= int(target_num):
                    found = True

            if found:
                info.append(f"  {visual_id}: Found matching image")
            else:
                warnings.append(f"  {visual_id}: No matching image found! Add image named '{target_num}.jpeg' or create image_registry.json")
    else:
        info.append("No visual assets defined in script (no floating images)")

    # Generate summary
    is_valid = len(errors) == 0
    if is_valid and len(warnings) == 0:
        summary = "All prerequisites validated successfully. Ready to render."
    elif is_valid:
        summary = f"Can render, but {len(warnings)} warning(s) found. Review warnings above."
    else:
        summary = f"Cannot render: {len(errors)} error(s) found. Fix errors before rendering."

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "summary": summary,
        "script_id": script_id,
        "characters_found": list(characters_used),
        "visual_assets_found": len(visual_assets_in_script)
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

    # === PRE-RENDER VALIDATION ===
    # Run comprehensive validation BEFORE starting render to catch issues early
    log("Running pre-render validation...")
    validation = validate_render_prerequisites(script_id, shorts_dir, base_dir)

    # Log validation results
    for info_msg in validation.get("info", []):
        log(f"  [INFO] {info_msg}")
    for warn_msg in validation.get("warnings", []):
        log(f"  [WARNING] {warn_msg}", "WARN")
    for err_msg in validation.get("errors", []):
        log(f"  [ERROR] {err_msg}", "ERROR")

    log(f"Validation summary: {validation['summary']}")

    # Return errors immediately to save time
    if not validation["valid"]:
        return {
            "status": "validation_failed",
            "message": validation["summary"],
            "validation": validation,
            "action_required": "Fix the errors listed above before rendering. Check character images and visual assets."
        }

    # Show warnings but continue
    if validation.get("warnings"):
        log(f"Continuing with {len(validation['warnings'])} warning(s)...", "WARN")

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

    # Validate images catalog
    try:
        loader = ImageLoader(base_dir)
        validation = loader.validate_catalog()
        if not validation["valid"]:
            log(f"Image catalog validation failed: {validation}", "WARN")
    except Exception as e:
        log(f"Could not validate image catalog: {e}", "WARN")

    # Build render plan
    render_plan = {
        "script_id": script_id,
        "config": SHORT_CONFIG,
        "hook_text": hook_text,
        "opening_image": opening_image,
        "audio_file": str(audio_path),
        "timestamps_file": str(timestamps_path) if has_timestamps else None,
        "output_file": str(output_path),
        "character_mapping": CHARACTER_MAPPING,
        "available_poses": list(STANDARD_POSES.keys())
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
            "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
            "lip_sync": SHORT_CONFIG["lip_sync"]["enabled"]
        },
        "render_command": f"""
To render the video, run execute_render with the same parameters.
""",
        "preview_elements": {
            "hook_text": {
                "text": hook_text,
                "position": "top center",
                "style": "Bold white with black stroke"
            },
            "characters": "Analyst & Skeptic (with lip-sync)",
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
    Features:
    - Lip-sync animation (open/closed mouth based on word timing)
    - Pose switching based on script character_poses
    - Standardized image loading via ImageLoader
    """
    import traceback

    # Clear log file and start fresh
    clear_log()
    update_render_status("starting", "Initializing render...", 0)

    log("=" * 60)
    log("EXECUTE_RENDER STARTED (v2.0 with lip-sync)")
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

        # === COMPREHENSIVE PRE-RENDER VALIDATION ===
        # This catches issues with character images and visual assets BEFORE wasting render time
        log("Running comprehensive pre-render validation...")
        validation = validate_render_prerequisites(script_id, shorts_dir, base_dir)

        # Log validation results clearly
        log("-" * 40)
        for info_msg in validation.get("info", []):
            log(f"  [INFO] {info_msg}")
        for warn_msg in validation.get("warnings", []):
            log(f"  [WARN] {warn_msg}", "WARN")
        for err_msg in validation.get("errors", []):
            log(f"  [ERROR] {err_msg}", "ERROR")
        log(f"Validation result: {validation['summary']}")
        log("-" * 40)

        # STOP EARLY if validation fails
        if not validation["valid"]:
            update_render_status("error", f"Validation failed: {validation['summary']}", 0)
            return {
                "status": "validation_failed",
                "message": validation["summary"],
                "validation": validation,
                "action_required": "\n".join([
                    "Fix the following errors before rendering:",
                    *[f"  - {e}" for e in validation.get("errors", [])]
                ]),
                "log_file": str(LOG_FILE)
            }

        # Show warnings but continue
        if validation.get("warnings"):
            log(f"Proceeding with {len(validation['warnings'])} warning(s)...", "WARN")

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

        # Initialize ImageLoader
        log("Step 3: Initializing ImageLoader...")
        try:
            image_loader = ImageLoader(base_dir, preload=True)
            catalog_summary = image_loader.get_catalog_summary()
            log(f"ImageLoader initialized: {catalog_summary['total_poses']} poses loaded")
            for pose_id in catalog_summary['available_poses']:
                log(f"  - {pose_id}")
        except Exception as e:
            log(f"ImageLoader failed: {e}", "ERROR")
            return {
                "status": "error",
                "message": f"Failed to load images catalog: {e}",
                "action_required": "Ensure data/images/images_catalog.json exists and is valid"
            }

        # Validate catalog
        validation = image_loader.validate_catalog()
        if not validation["valid"]:
            log(f"Image catalog validation FAILED", "ERROR")
            for missing in validation["missing_files"]:
                log(f"  Missing: {missing}", "ERROR")
            return {
                "status": "error",
                "message": "Image catalog validation failed",
                "missing_files": validation["missing_files"],
                "load_errors": validation["load_errors"]
            }
        log("Image catalog validation OK")

        # Build render timeline
        log("Step 4: Building render timeline...")
        render_timeline = build_render_timeline(timestamps_data, script_data)
        log(f"Render timeline: {len(render_timeline)} segments")

        # Prepare output
        log("Step 5: Preparing output...")
        output_dir = shorts_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{output_filename}.mp4"
        log(f"Output path: {output_path}")

        # Create renderer and render video
        log("Step 6: Creating ShortVideoRenderer...")
        renderer = ShortVideoRenderer(
            config=SHORT_CONFIG,
            base_dir=base_dir,
            image_loader=image_loader
        )
        log("Renderer created OK")

        log("Step 7: Starting render...")
        update_render_status("rendering", "Starting video render...", 5, {"total_frames": "calculating..."})
        # Run the CPU-intensive render in a thread pool to avoid blocking MCP event loop
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context (MCP server), use thread pool
            result = await asyncio.to_thread(
                renderer.render,
                audio_path=str(audio_path),
                timestamps_data=timestamps_data,
                script_data=script_data,
                render_timeline=render_timeline,
                hook_text=hook_text,
                opening_image=opening_image,
                output_path=str(output_path)
            )
        except RuntimeError:
            # No running event loop (direct CLI execution)
            result = renderer.render(
                audio_path=str(audio_path),
                timestamps_data=timestamps_data,
                script_data=script_data,
                render_timeline=render_timeline,
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
                "message": f"Video rendered successfully with lip-sync!",
                "video_specs": {
                    "dimensions": f"{SHORT_CONFIG['width']}x{SHORT_CONFIG['height']}",
                    "format": "MP4 (H.264)",
                    "platforms": ["TikTok", "Instagram Reels", "YouTube Shorts"],
                    "lip_sync": True,
                    "poses_used": result.get("poses_used", [])
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


def execute_render_sync(
    script_id: str,
    hook_text: str,
    opening_image: str = "",
    output_filename: str = "short_video",
    shorts_dir: Path = None
) -> dict:
    """
    Synchronous version of execute_render for use in background worker process.
    This runs the entire render without any async overhead.
    """
    import asyncio

    # Create a new event loop and run the async function
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            execute_render(
                script_id=script_id,
                hook_text=hook_text,
                opening_image=opening_image,
                output_filename=output_filename,
                shorts_dir=shorts_dir
            )
        )
        return result
    finally:
        loop.close()


class ShortVideoRenderer:
    """
    Renderer for short-form videos (9:16 vertical format).
    Uses PyAV for efficient video encoding and ImageLoader for standardized image access.

    Features:
    - Lip-sync animation (open/closed mouth)
    - Pose-based character switching
    - Hook text overlay
    - Word-by-word captions
    """

    def __init__(self, config: dict, base_dir: Path, image_loader: ImageLoader):
        log("ShortVideoRenderer.__init__ starting...")
        self.config = config
        self.base_dir = Path(base_dir)
        self.image_loader = image_loader
        self.width = config["width"]
        self.height = config["height"]
        self.fps = config["fps"]
        self.bg_color = config["background_color"]

        log(f"Video config: {self.width}x{self.height} @ {self.fps}fps")

        # Images directory setup
        self.images_dir = self.base_dir / "data" / "images"

        # Font setup
        self.font_path = self.base_dir / "data" / "font" / "GoogleSans-SemiBold.ttf"
        self._font_cache = {}
        log(f"Font path: {self.font_path} (exists: {self.font_path.exists()})")

        # Lip sync config
        self.lip_sync_enabled = config.get("lip_sync", {}).get("enabled", True)
        self.open_threshold = config.get("lip_sync", {}).get("open_threshold", 0.05)
        log(f"Lip sync: {'enabled' if self.lip_sync_enabled else 'disabled'}")

        log("ShortVideoRenderer.__init__ complete")

    def _is_speaking(self, current_time: float, all_words: list) -> bool:
        """Check if any character is speaking at the given time."""
        for word in all_words:
            if word["start"] <= current_time <= word["end"]:
                return True
        return False

    def _calculate_floating_image_schedule(self, audio_duration: float, visual_assets: list) -> list:
        """
        Calculate when floating images should appear during the video.

        If visual_assets already have start_time/end_time (from _extract_visual_assets_from_dialogue),
        use those times directly. Otherwise, distribute evenly.

        Returns a list of dicts with:
        - image_path: path to the image
        - start_time: when to start showing
        - end_time: when to stop showing
        - fade_in_end: when fade-in completes
        - fade_out_start: when fade-out begins
        """
        floating_config = self.config.get("floating_images", {})

        if not floating_config.get("enabled", False) or not visual_assets:
            return []

        schedule = []
        fade_in = floating_config.get("fade_in", 0.5)
        fade_out = floating_config.get("fade_out", 0.5)

        for asset in visual_assets:
            # Check if asset already has timing from _extract_visual_assets_from_dialogue
            if "start_time" in asset and "end_time" in asset:
                start_time = asset["start_time"]
                end_time = asset["end_time"]

                # Opening images should appear instantly (no fade in) at frame 0
                is_opening = asset.get("is_opening", False)

                # Calculate fade times - opening images have no fade_in for instant appearance
                if is_opening:
                    # Opening image: instant appearance (fade_in_end = start_time)
                    asset_fade_in = 0.0
                    asset_fade_out = fade_out
                else:
                    asset_fade_in = fade_in
                    asset_fade_out = fade_out

                fade_in_end = start_time + asset_fade_in
                fade_out_start = end_time - asset_fade_out

                # Ensure fade times don't overlap
                if fade_in_end > fade_out_start:
                    mid = (start_time + end_time) / 2
                    fade_in_end = mid
                    fade_out_start = mid

                schedule.append({
                    "image_path": asset.get("path", asset.get("image_path", "")),
                    "description": asset.get("description", ""),
                    "visual_asset_id": asset.get("visual_asset_id", ""),
                    "start_time": start_time,
                    "end_time": end_time,
                    "fade_in_end": fade_in_end,
                    "fade_out_start": fade_out_start,
                    "is_opening": is_opening
                })

                log(f"Scheduled floating image '{asset.get('visual_asset_id', '')}': {start_time:.1f}s - {end_time:.1f}s (opening={is_opening})")

            else:
                # Fallback: use legacy uniform distribution
                # This path is kept for backward compatibility
                log(f"Asset missing timing, using legacy distribution", "WARN")

        # If no pre-timed assets, fall back to uniform distribution
        if not schedule and visual_assets:
            log("No pre-timed assets found, using uniform distribution")
            skip_start = floating_config.get("skip_first_seconds", 5)
            skip_end = floating_config.get("skip_last_seconds", 5)
            display_duration = floating_config.get("display_duration", 5)

            available_start = skip_start
            available_end = audio_duration - skip_end

            if available_end > available_start:
                num_images = len(visual_assets)
                spacing = (available_end - available_start) / (num_images + 1)

                for i, asset in enumerate(visual_assets):
                    start_time = available_start + spacing * (i + 1) - display_duration / 2
                    start_time = max(available_start, min(start_time, available_end - display_duration))
                    end_time = start_time + display_duration
                    fade_in_end = start_time + fade_in
                    fade_out_start = end_time - fade_out

                    schedule.append({
                        "image_path": asset.get("path", asset.get("image_path", "")),
                        "description": asset.get("description", ""),
                        "start_time": start_time,
                        "end_time": end_time,
                        "fade_in_end": fade_in_end,
                        "fade_out_start": fade_out_start
                    })

        return schedule

    def _get_floating_image_opacity(self, current_time: float, schedule_item: dict) -> float:
        """Calculate opacity for a floating image based on current time."""
        start_time = schedule_item["start_time"]
        end_time = schedule_item["end_time"]
        fade_in_end = schedule_item["fade_in_end"]
        fade_out_start = schedule_item["fade_out_start"]

        if current_time < start_time or current_time > end_time:
            return 0.0

        # Fade in
        if current_time < fade_in_end:
            progress = (current_time - start_time) / (fade_in_end - start_time)
            return max(0.0, min(1.0, progress))

        # Fade out
        if current_time > fade_out_start:
            progress = (end_time - current_time) / (end_time - fade_out_start)
            return max(0.0, min(1.0, progress))

        # Full opacity
        return 1.0

    def _apply_blur_to_region(self, image, blur_radius: int = 15):
        """Apply Gaussian blur to an image."""
        from PIL import ImageFilter
        return image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    def _load_floating_image(self, image_path: str) -> Optional[any]:
        """Load a floating image from path."""
        from PIL import Image

        if not image_path:
            return None

        # Try different base paths
        possible_paths = [
            Path(image_path),  # Absolute path
            self.base_dir / image_path,  # Relative to base
            self.base_dir / "data" / "images" / image_path,  # In images folder
            self.base_dir / "data" / "shorts" / "images" / image_path,  # In shorts images
        ]

        for path in possible_paths:
            if path.exists():
                try:
                    img = Image.open(path).convert("RGBA")
                    log(f"Loaded floating image: {path}")
                    return img
                except Exception as e:
                    log(f"Error loading floating image {path}: {e}", "WARN")

        log(f"Floating image not found: {image_path}", "WARN")
        return None

    def _extract_visual_assets_from_dialogue(
        self,
        script_data: Dict[str, Any],
        timestamps_data: Dict[str, Any],
        base_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Extract visual_assets from dialogue items and map them to actual image files.

        This function:
        1. Handles opening_visual FIRST (appears before/during first dialogue)
        2. Extracts visual_assets from each dialogue line
        3. Maps visual_asset_id to registered images in data/shorts/images/
        4. Calculates timing: images appear at MIDPOINT of the dialogue segment
        5. Returns a list ready for the floating image scheduler

        Args:
            script_data: The script with dialogue containing visual_assets
            timestamps_data: Word-level timestamps for timing
            base_dir: Base directory of the project

        Returns:
            List of visual assets with paths and timing info
        """
        visual_assets = []

        # Get script content
        script = script_data.get("script", script_data)

        # Get dialogue from script
        dialogue = script.get("dialogue", [])

        # Get timestamp segments for timing
        segments = timestamps_data.get("segments", [])

        # Load image registry to map visual_asset_id to actual files
        image_registry = self._load_image_registry(base_dir)

        log(f"Extracting visual assets from {len(dialogue)} dialogue lines")
        log(f"Image registry has {len(image_registry)} mapped images")

        # === HANDLE OPENING_VISUAL FIRST ===
        # The opening_visual appears BEFORE or at the START of the first dialogue
        # It shows the image first, then the character speaks in the background
        opening_visual = script.get("opening_visual", {})
        if opening_visual:
            opening_duration = opening_visual.get("duration_seconds", 3.0)

            # Find opening image - try registry first, then by name
            opening_image_path = None

            # Check if there's an "opening" entry in the registry
            opening_image_path = image_registry.get("opening", "")
            if not opening_image_path:
                opening_image_path = image_registry.get("0a", "")
            if not opening_image_path:
                # Try to find by naming convention
                opening_image_path = self._find_image_by_convention("opening", base_dir)
            if not opening_image_path:
                # Try primer.jpeg as opening image (first image in folder)
                opening_image_path = self._find_image_by_convention("1a", base_dir)

            if opening_image_path:
                # Opening visual behavior:
                # - Video starts with opening image visible
                # - Character is ALREADY speaking in the background (audio plays from start)
                # - At MIDPOINT of first dialogue text, the opening image fades out
                # - Then we see the character speaking normally
                #
                # Timeline:
                # 0s ----[Opening Image]---- midpoint ----[Character visible]---- end of first dialogue

                end_time = opening_duration  # Default fallback

                if segments:
                    first_seg = segments[0]
                    first_seg_start = first_seg.get("start", 0)
                    first_seg_end = first_seg.get("end", opening_duration)
                    first_seg_duration = first_seg_end - first_seg_start

                    # Opening ends at midpoint of first dialogue segment
                    # The character is speaking from start, but we only see them after midpoint
                    end_time = first_seg_start + (first_seg_duration / 2)

                    log(f"  Opening visual: first segment {first_seg_start:.1f}s - {first_seg_end:.1f}s, midpoint at {end_time:.1f}s")

                visual_assets.append({
                    "visual_asset_id": "opening",
                    "path": opening_image_path,
                    "image_path": opening_image_path,
                    "description": opening_visual.get("image_prompt", "Opening visual"),
                    "start_time": 0.0,
                    "end_time": end_time,
                    "is_opening": True,
                    "dialogue_index": -1,  # Before any dialogue
                    "segment_start": 0,
                    "segment_end": end_time
                })
                log(f"  Opening visual -> {opening_image_path} (0.0s - {end_time:.1f}s)")
            else:
                log(f"  WARNING: No image found for opening_visual", "WARN")

        for idx, line in enumerate(dialogue):
            line_visual_assets = line.get("visual_assets", [])
            if not line_visual_assets:
                continue

            # Get timing from corresponding timestamp segment
            if idx < len(segments):
                seg = segments[idx]
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", 0)
                seg_duration = seg_end - seg_start

                # Calculate midpoint - image appears at midpoint of dialogue
                midpoint = seg_start + (seg_duration / 2)

                # Each visual asset gets time from midpoint to end
                remaining_duration = seg_end - midpoint
                num_assets = len(line_visual_assets)
                asset_duration = remaining_duration / num_assets if num_assets > 0 else 0

                for v_idx, va in enumerate(line_visual_assets):
                    visual_id = va.get("visual_asset_id", "")

                    # Find actual image path from registry
                    image_path = image_registry.get(visual_id, "")

                    if not image_path:
                        # Try to find by index-based naming convention
                        # e.g., "1a" -> "primer.jpeg", "2a" -> "segundo.jpeg"
                        image_path = self._find_image_by_convention(visual_id, base_dir)

                    if image_path:
                        start_time = midpoint + (v_idx * asset_duration)
                        end_time = start_time + asset_duration

                        # Ensure we don't exceed segment end
                        if v_idx == num_assets - 1:
                            end_time = seg_end

                        visual_assets.append({
                            "visual_asset_id": visual_id,
                            "path": image_path,
                            "image_path": image_path,  # Alias for compatibility
                            "description": va.get("image_prompt", ""),
                            "start_time": start_time,
                            "end_time": end_time,
                            "dialogue_index": idx,
                            "segment_start": seg_start,
                            "segment_end": seg_end
                        })
                        log(f"  Visual asset '{visual_id}' -> {image_path} ({start_time:.1f}s - {end_time:.1f}s)")
                    else:
                        log(f"  WARNING: No image found for visual_asset_id '{visual_id}'", "WARN")

        log(f"Total visual assets extracted: {len(visual_assets)}")
        return visual_assets

    def _load_image_registry(self, base_dir: Path) -> Dict[str, str]:
        """
        Load the image registry that maps visual_asset_id to actual file paths.

        The registry is stored at data/shorts/images/image_registry.json
        """
        registry_path = base_dir / "data" / "shorts" / "images" / "image_registry.json"
        images_dir = base_dir / "data" / "shorts" / "images"

        if not registry_path.exists():
            log(f"Image registry not found at {registry_path}", "WARN")
            return {}

        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Build mapping from visual_asset_id to ABSOLUTE path
            mapping = {}

            def resolve_path(relative_path: str) -> str:
                """Convert relative path to absolute path."""
                if not relative_path:
                    return ""
                # If already absolute, return as-is
                if Path(relative_path).is_absolute():
                    return relative_path
                # Otherwise, resolve relative to images_dir
                full_path = images_dir / relative_path
                if full_path.exists():
                    return str(full_path)
                return ""  # Return empty if file doesn't exist

            # Handle structure: {"images": [...], "scripts": {...}}
            images = data.get("images", [])
            for img in images:
                vid = img.get("visual_asset_id", "")
                path = img.get("path", "")
                if vid and path:
                    resolved = resolve_path(path)
                    if resolved:
                        mapping[vid] = resolved
                        log(f"  Registry: {vid} -> {resolved}")
                    else:
                        log(f"  Registry: {vid} -> {path} (FILE NOT FOUND)", "WARN")

            # Also check for script-specific mappings (these override global)
            scripts = data.get("scripts", {})
            for sid, script_mapping in scripts.items():
                # Support both dict format and list format
                if isinstance(script_mapping, dict):
                    # Dict format: {"1a": "1.jpeg", "2a": "2.jpeg"}
                    for vid, path in script_mapping.items():
                        if vid.startswith("_"):  # Skip meta fields like "_note"
                            continue
                        if isinstance(path, str):
                            resolved = resolve_path(path)
                            if resolved:
                                mapping[vid] = resolved
                elif isinstance(script_mapping, list):
                    # List format: [{"visual_asset_id": "1a", "path": "1.jpeg"}]
                    for img in script_mapping:
                        if isinstance(img, dict):
                            vid = img.get("visual_asset_id", "")
                            path = img.get("path", "")
                            if vid and path:
                                resolved = resolve_path(path)
                                if resolved:
                                    mapping[vid] = resolved

            log(f"Image registry loaded: {len(mapping)} mappings")
            return mapping

        except Exception as e:
            log(f"Error loading image registry: {e}", "ERROR")
            return {}

    def _find_image_by_convention(self, visual_id: str, base_dir: Path) -> Optional[str]:
        """
        Find image by naming convention when not in registry.

        Convention mapping:
        - "1a" -> looks for "1.jpeg", "primer.jpeg", etc.
        - "2a" -> looks for "2.jpeg", "segundo.jpeg", etc.
        - etc.

        Also tries direct file matching in data/shorts/images/
        """
        import re

        images_dir = base_dir / "data" / "shorts" / "images"

        if not images_dir.exists():
            log(f"Images directory not found: {images_dir}", "WARN")
            return None

        # Get all image files
        image_extensions = [".jpeg", ".jpg", ".png", ".webp"]
        image_files = []
        for ext in image_extensions:
            image_files.extend(images_dir.glob(f"*{ext}"))

        # Filter out registry file
        image_files = [f for f in image_files if f.suffix.lower() in image_extensions]

        log(f"Looking for image with visual_id '{visual_id}' in {images_dir}")
        log(f"  Available images: {[f.name for f in image_files]}")

        # Extract numeric index from visual_id (e.g., "1a" -> 1, "2a" -> 2, "opening" -> None)
        match = re.match(r"(\d+)", visual_id)
        target_index = int(match.group(1)) if match else None

        # PRIORITY 1: Exact match on filename (without extension)
        # e.g., visual_id="1a" matches "1a.jpeg", "1a.png"
        for img_file in image_files:
            if img_file.stem.lower() == visual_id.lower():
                log(f"  Found exact match: {img_file}")
                return str(img_file)

        # PRIORITY 2: Numeric filename match (e.g., "1a" matches "1.jpeg")
        if target_index is not None:
            for img_file in image_files:
                # Check if filename is exactly the number
                if img_file.stem == str(target_index):
                    log(f"  Found numeric match: {img_file}")
                    return str(img_file)

        # PRIORITY 3: Spanish/English name convention
        index_to_names = {
            1: ["primer", "primero", "first", "opening"],
            2: ["segundo", "second"],
            3: ["tercer", "tercero", "third"],
            4: ["cuarto", "fourth"],
            5: ["quinto", "quinta", "fifth"],
            6: ["sexto", "sexta", "sixth"],
            7: ["septimo", "seventh"],
            8: ["octavo", "eighth"],
            9: ["noveno", "ninth"],
            10: ["decimo", "tenth"],
        }

        if target_index and target_index in index_to_names:
            names_to_try = index_to_names[target_index]
            for img_file in image_files:
                stem_lower = img_file.stem.lower()
                for name in names_to_try:
                    if stem_lower == name or stem_lower.startswith(name):
                        log(f"  Found convention match ({name}): {img_file}")
                        return str(img_file)

        # PRIORITY 4: Sort numerically and get by index position
        # This handles cases like having files: 1.jpeg, 2.jpeg, 3.jpeg
        if target_index is not None:

            def numeric_sort_key(f):
                """Extract leading number from filename for numeric sort."""
                m = re.match(r"(\d+)", f.stem)
                return int(m.group(1)) if m else float('inf')

            # Filter to only numeric-named files for position-based matching
            numeric_files = [f for f in image_files if re.match(r"^\d+$", f.stem)]
            if numeric_files:
                sorted_files = sorted(numeric_files, key=numeric_sort_key)
                # target_index is 1-based, convert to 0-based
                idx = target_index - 1
                if 0 <= idx < len(sorted_files):
                    log(f"  Found by numeric position [{idx}]: {sorted_files[idx]}")
                    return str(sorted_files[idx])

        # PRIORITY 5: Fallback - any file containing the visual_id
        for img_file in image_files:
            if visual_id.lower() in img_file.stem.lower():
                log(f"  Found partial match: {img_file}")
                return str(img_file)

        log(f"  No image found for visual_id '{visual_id}'", "WARN")
        return None

    def _should_mouth_be_open(self, current_time: float, all_words: list) -> bool:
        """
        Determine if mouth should be open using syllable-based animation.
        More natural than simple on/off - simulates actual speech patterns.

        Improved algorithm:
        - Each word gets 1 mouth cycle per syllable (counted via vowels)
        - Minimum 1 cycle per word, even for short words
        - Cycles are distributed evenly across the word duration
        - Mouth opens/closes faster for more natural speech appearance
        """
        lip_config = self.config.get("lip_sync", {})
        mode = lip_config.get("mode", "syllable")

        # Find current word being spoken
        current_word = None
        for word in all_words:
            if word["start"] <= current_time <= word["end"]:
                current_word = word
                break

        if not current_word:
            return False  # Not speaking

        word_text = current_word.get("text", "")
        word_start = current_word["start"]
        word_end = current_word["end"]
        word_duration = word_end - word_start

        if word_duration <= 0:
            return False

        # Check for punctuation - close mouth on pauses
        if lip_config.get("respect_punctuation", True):
            punctuation = ".,;:!?…"
            if word_text and word_text[-1] in punctuation:
                # Close mouth for last 20% of word with punctuation (faster close)
                progress = (current_time - word_start) / word_duration
                if progress > 0.8:
                    return False

        if mode == "fast":
            # Rapid cycling mode (12 times/second for faster lip movement)
            cycle_position = (current_time * 12) % 1.0
            return cycle_position < 0.5

        # Syllable-based mode (default) - IMPROVED
        vowels = lip_config.get("vowels", "aeiouáéíóúAEIOUÁÉÍÓÚ")
        open_ratio = lip_config.get("open_ratio", 0.55)
        min_syllable_ms = lip_config.get("min_syllable_ms", 60)
        max_syllable_ms = lip_config.get("max_syllable_ms", 120)

        # Count vowels (approximate syllables)
        # Also count consonant clusters as potential syllable breaks
        vowel_count = sum(1 for c in word_text if c in vowels)
        syllable_count = max(1, vowel_count)

        # For single-syllable words, ensure at least one full open/close cycle
        # For multi-syllable words, match cycles to syllables
        time_in_word = current_time - word_start

        # Calculate actual syllable duration based on word duration
        # Each syllable gets equal time within the word
        syllable_duration_sec = word_duration / syllable_count

        # Clamp syllable duration to reasonable bounds
        min_dur = min_syllable_ms / 1000.0
        max_dur = max_syllable_ms / 1000.0

        # If natural syllable duration is too slow, add more cycles
        if syllable_duration_sec > max_dur:
            # Add extra cycles to make animation faster
            extra_cycles = int(syllable_duration_sec / max_dur)
            syllable_count = syllable_count * max(1, extra_cycles)
            syllable_duration_sec = word_duration / syllable_count

        # If natural syllable duration is too fast, slow it down
        if syllable_duration_sec < min_dur and syllable_count > 1:
            # Reduce cycles to prevent too-fast animation
            syllable_count = max(1, int(word_duration / min_dur))
            syllable_duration_sec = word_duration / syllable_count

        # Which syllable cycle are we in?
        current_syllable = int(time_in_word / syllable_duration_sec) if syllable_duration_sec > 0 else 0
        current_syllable = min(current_syllable, syllable_count - 1)

        # Position within current syllable (0.0 to 1.0)
        syllable_start_time = current_syllable * syllable_duration_sec
        position_in_syllable = (time_in_word - syllable_start_time) / syllable_duration_sec if syllable_duration_sec > 0 else 0
        position_in_syllable = max(0.0, min(1.0, position_in_syllable))

        # Mouth open for first portion of syllable, closed for rest
        # This creates the open-close-open-close pattern for each syllable
        return position_in_syllable < open_ratio

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

        # Supported image extensions (in order of preference)
        extensions = [".png", ".jpeg", ".jpg", ".webp"]

        # Build possible paths based on actual directory structure
        # Structure: data/images/{character}/{pose}_view/{Pose}Mouth_{State}.{ext}
        possible_paths = []

        # Base patterns to try (without extension)
        base_patterns = [
            # New structure: analyst/close_view/CloseMouth_Open
            self.images_dir / char_lower / pose_dir / f"CloseMouth_{mouth_state}",
            self.images_dir / char_lower / pose_dir / f"FrontMouth_{mouth_state}",
            self.images_dir / char_lower / pose_dir / f"SideMouth_{mouth_state}",
            self.images_dir / char_lower / pose_dir / f"PovMouth_{mouth_state}",
            # Generic pattern
            self.images_dir / char_lower / pose_dir / f"{pose.capitalize()}Mouth_{mouth_state}",
            # Fallback to old flat structure
            self.images_dir / f"{char_lower}_{pose}",
            self.images_dir / f"{char_lower}",
        ]

        # Add all extension variants for each pattern
        for base in base_patterns:
            for ext in extensions:
                possible_paths.append(Path(str(base) + ext))

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
        pose_id: str,
        mouth_open: bool,
        caption_text: str,
        hook_text: str,
        floating_image: any = None,
        floating_opacity: float = 0.0,
        hide_captions_for_floating: bool = False,
        is_opening_image: bool = False
    ) -> any:
        """Create a single video frame with the specified character pose and mouth state.

        Args:
            character: Character name
            pose_id: Pose identifier
            mouth_open: Whether mouth should be open
            caption_text: Text to show as caption
            hook_text: Text to show at top
            floating_image: Optional PIL Image to overlay with blur effect
            floating_opacity: Opacity of the floating image (0.0 to 1.0)
            hide_captions_for_floating: If True, hide captions when floating image is shown
            is_opening_image: If True, skip blur effect for clean thumbnail/first frame
        """
        from PIL import Image, ImageDraw, ImageFilter
        import numpy as np

        # Create base frame with background color
        frame = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(frame)

        # 1. Draw character image (centered in character area)
        character_image = None
        if pose_id:
            character_image = self.image_loader.get_image(pose_id, mouth_open=mouth_open)

        if character_image is None:
            # Fall back to default pose
            character_image = self.image_loader.get_default_image(character, mouth_open=mouth_open)

        if character_image:
            # Character images should COVER the entire canvas (1080x1920)
            # Using "cover" mode: scale and crop to fill, maintaining aspect ratio
            from PIL import ImageOps

            # Use ImageOps.fit for "cover" behavior - scales and crops to exact dimensions
            # The image will fill the entire canvas, cropping if necessary to maintain aspect ratio
            resized = ImageOps.fit(
                character_image,
                (self.width, self.height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5)  # Center the crop horizontally and vertically
            )

            # Position at origin (0,0) since image now covers full canvas
            x = 0
            y = 0

            # Paste with alpha if available
            if resized.mode == 'RGBA':
                frame.paste(resized, (x, y), resized)
            else:
                frame.paste(resized, (x, y))

        # 2. Draw hook text at top (BEFORE blur for normal images, AFTER for opening)
        # For opening image: skip drawing here, will draw after floating image (no blur on title)
        if hook_text and not is_opening_image:
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

        # 3. Draw floating image with blur effect (if provided)
        # ALWAYS blur the character background when showing a floating image (including opening)
        # The illustration and title should be clear, but the character behind is blurred
        if floating_image is not None and floating_opacity > 0:
            floating_cfg = self.config.get("floating_images", {})
            blur_radius = floating_cfg.get("background_blur", 15)
            size_ratio = floating_cfg.get("size_ratio", 0.6)
            y_position = floating_cfg.get("y_position", 0.45)

            # Calculate floating image size
            target_width = int(self.width * size_ratio)
            img_ratio = floating_image.width / floating_image.height
            target_height = int(target_width / img_ratio)

            # Resize floating image
            resized_floating = floating_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Center horizontally, position vertically
            float_x = (self.width - target_width) // 2
            float_y = int(self.height * y_position) - target_height // 2

            # ALWAYS apply blur to character background when showing floating image
            # This makes the illustration stand out clearly
            blurred_frame = frame.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            # Create composite: blurred background + floating image
            # For opening image, use stronger blur effect to make illustration pop
            blur_blend = floating_opacity * 0.85 if is_opening_image else floating_opacity * 0.7
            frame = Image.blend(frame, blurred_frame, blur_blend)

            # Paste floating image with alpha
            if resized_floating.mode == 'RGBA':
                # Apply opacity to alpha channel
                r, g, b, a = resized_floating.split()
                a = a.point(lambda x: int(x * floating_opacity))
                resized_floating = Image.merge('RGBA', (r, g, b, a))
                frame.paste(resized_floating, (float_x, float_y), resized_floating)
            else:
                # Create temporary RGBA for blending
                temp = Image.new('RGBA', frame.size, (0, 0, 0, 0))
                temp.paste(resized_floating, (float_x, float_y))
                frame = Image.alpha_composite(frame.convert('RGBA'), temp).convert('RGB')

            # Update draw object for new frame
            draw = ImageDraw.Draw(frame)

        # 2b. Draw hook text AFTER floating image for opening (clean, no blur)
        if hook_text and is_opening_image:
            hook_cfg = self.config["hook_text"]
            font_size = int(self.height * hook_cfg["font_size_ratio"])
            font = self._get_font(font_size)

            y_pos = int(self.height * hook_cfg["y_position"])

            # Draw with stroke for visibility (crisp, no blur)
            self._draw_text_with_stroke(
                draw, hook_text, font,
                x=self.width // 2,
                y=y_pos,
                text_color=tuple(hook_cfg["color"]),
                stroke_color=tuple(hook_cfg["stroke_color"]),
                stroke_width=hook_cfg["stroke_width"],
                anchor="mt"  # Middle-Top
            )

        # 4. Draw caption at bottom (optionally hidden during floating image)
        should_show_caption = caption_text and not (hide_captions_for_floating and floating_opacity > 0.5)
        if should_show_caption:
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
        script_data: dict,
        render_timeline: List[RenderSegment],
        hook_text: str,
        opening_image: str,
        output_path: str
    ) -> dict:
        """
        Render the complete video with lip-sync and pose switching.
        """
        log("=" * 50)
        log("ShortVideoRenderer.render() STARTING")
        log(f"audio_path: {audio_path}")
        log(f"hook_text: {hook_text}")
        log(f"output_path: {output_path}")
        log(f"render_timeline segments: {len(render_timeline)}")
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

            # Build word timeline for lip sync
            segments = timestamps_data.get("segments", [])
            log(f"Segments in timestamps: {len(segments)}")

            # Build a flat list of all words with timing
            all_words = []
            total_words = 0
            for segment in segments:
                character = segment.get("character", "Analyst")
                character = CHARACTER_MAPPING.get(character, character)

                for word in segment.get("words", []):
                    word_text = word.get("text", word.get("word", "")).strip()
                    if word_text and word.get("start") is not None:
                        all_words.append({
                            "start": word["start"],
                            "end": word["end"],
                            "text": word_text,
                            "character": character
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
            output_container = None  # Initialize to None for proper cleanup
            output_container = av.open(output_path, mode='w')

            # Determine codec to use (GPU or CPU)
            gpu_config = self.config.get("gpu_encoding", {})
            use_gpu = gpu_config.get("enabled", False)
            video_codec = self.config["video_codec"]  # Default CPU codec

            if use_gpu:
                nvidia_codec = gpu_config.get("nvidia_codec", "h264_nvenc")
                try:
                    # Try to create GPU stream
                    log(f"Attempting GPU encoding with {nvidia_codec}...")
                    video_stream = output_container.add_stream(nvidia_codec, rate=self.fps)
                    video_stream.width = self.width
                    video_stream.height = self.height
                    video_stream.pix_fmt = 'yuv420p'
                    video_stream.bit_rate = int(self.config["video_bitrate"].replace("M", "000000"))

                    # Set NVENC-specific options
                    video_stream.options = {
                        'preset': gpu_config.get("nvidia_preset", "p4"),
                        'tune': gpu_config.get("nvidia_tune", "hq"),
                        'rc': 'vbr',  # Variable bitrate
                    }
                    video_codec = nvidia_codec
                    log(f"GPU encoding enabled: {nvidia_codec} (preset: {gpu_config.get('nvidia_preset', 'p4')})")
                except Exception as gpu_error:
                    log(f"GPU encoding failed: {gpu_error}", "WARN")
                    if gpu_config.get("fallback_to_cpu", True):
                        log("Falling back to CPU encoding...")
                        # Close and reopen container for CPU
                        output_container.close()
                        output_container = av.open(output_path, mode='w')
                        use_gpu = False
                    else:
                        raise gpu_error

            if not use_gpu:
                # Add CPU video stream
                log("Using CPU encoding...")
                video_stream = output_container.add_stream(video_codec, rate=self.fps)
                video_stream.width = self.width
                video_stream.height = self.height
                video_stream.pix_fmt = 'yuv420p'
                video_stream.bit_rate = int(self.config["video_bitrate"].replace("M", "000000"))

            log(f"Video stream: {self.width}x{self.height}, codec={video_codec}, GPU={use_gpu}")

            # Build captions timeline from all_words
            captions_timeline = all_words

            # Create helper function to get pose and character for a given time
            def get_pose_and_character(t: float) -> tuple:
                """Get the character and pose for a given timestamp."""
                for seg in segments:
                    seg_start = seg.get("start", 0)
                    seg_end = seg.get("end", 0)
                    if seg_start <= t <= seg_end:
                        char = seg.get("character", "Analyst")
                        char = CHARACTER_MAPPING.get(char, char)
                        # Default pose based on character
                        pose = f"{char.lower()}_front"
                        return char, pose
                # Default to Analyst if no segment matches
                return "Analyst", "analyst_front"

            # Track poses used and current character
            poses_used = set()
            current_character = "Analyst"

            # Setup floating images - extract from dialogue items AND map to registered images
            visual_assets = self._extract_visual_assets_from_dialogue(
                script_data, timestamps_data, self.base_dir
            )
            log(f"Visual assets extracted from dialogue: {len(visual_assets)}")

            floating_image_schedule = self._calculate_floating_image_schedule(audio_duration, visual_assets)
            log(f"Floating image schedule: {len(floating_image_schedule)} images")

            # Pre-load floating images
            floating_images_cache = {}
            for schedule_item in floating_image_schedule:
                img_path = schedule_item.get("image_path", "")
                if img_path and img_path not in floating_images_cache:
                    floating_images_cache[img_path] = self._load_floating_image(img_path)
            log(f"Pre-loaded {len(floating_images_cache)} floating images")

            floating_cfg = self.config.get("floating_images", {})
            hide_captions_for_floating = floating_cfg.get("hide_captions", True)

            # Render frames
            total_frames = int(audio_duration * self.fps)
            log(f"Starting frame render: {total_frames} frames")

            for frame_idx in range(total_frames):
                current_time = frame_idx / self.fps

                # Get character and pose for current time
                character, pose_id = get_pose_and_character(current_time)
                poses_used.add(pose_id)

                # Check if currently speaking (for lip sync)
                mouth_open = False
                if self.lip_sync_enabled:
                    mouth_open = self._is_speaking(current_time, all_words)

                # Find active caption word
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

                # Get character image with mouth animation using improved syllable-based lip-sync
                char_data = character_images.get(current_character)
                char_img = None
                if char_data:
                    if is_speaking:
                        # Use new syllable-based lip-sync method
                        mouth_open = self._should_mouth_be_open(current_time, all_words)
                        char_img = char_data["open"] if mouth_open else char_data["closed"]
                    else:
                        # Not speaking - mouth closed
                        char_img = char_data["closed"]

                # Check if we should show a floating image at this time
                current_floating_image = None
                current_floating_opacity = 0.0
                current_is_opening = False
                for schedule_item in floating_image_schedule:
                    if schedule_item["start_time"] <= current_time <= schedule_item["end_time"]:
                        img_path = schedule_item.get("image_path", "")
                        current_floating_image = floating_images_cache.get(img_path)
                        current_floating_opacity = self._get_floating_image_opacity(current_time, schedule_item)
                        current_is_opening = schedule_item.get("is_opening", False)
                        break

                # Create frame
                frame_array = self._create_frame(
                    character=character,
                    pose_id=pose_id,
                    mouth_open=mouth_open,
                    caption_text=active_caption,
                    hook_text=hook_text,
                    floating_image=current_floating_image,
                    floating_opacity=current_floating_opacity,
                    hide_captions_for_floating=hide_captions_for_floating,
                    is_opening_image=current_is_opening
                )

                # Encode frame
                frame = av.VideoFrame.from_ndarray(frame_array, format='rgb24')
                frame.pts = frame_idx

                for packet in video_stream.encode(frame):
                    output_container.mux(packet)

                # Progress indicator every 5 seconds (more frequent updates)
                if frame_idx % (self.fps * 5) == 0:
                    progress = (frame_idx / total_frames) * 100
                    log(f"Render progress: {progress:.1f}% ({frame_idx}/{total_frames})")
                    # Update status file for real-time tracking
                    update_render_status(
                        "rendering",
                        f"Rendering frame {frame_idx}/{total_frames}",
                        5 + (progress * 0.85),  # 5-90% for rendering phase
                        {"frame": frame_idx, "total_frames": total_frames, "percent": round(progress, 1)}
                    )

            log("Flushing video encoder...")
            update_render_status("encoding", "Flushing video encoder...", 90)
            # Flush video encoder
            for packet in video_stream.encode():
                output_container.mux(packet)

            output_container.close()
            log("Video container closed")

            # Now mux audio with video using ffmpeg (with background music mixing)
            log("Adding audio track with FFmpeg...")
            update_render_status("muxing", "Adding audio track...", 92)
            temp_output = output_path.replace(".mp4", "_temp.mp4")
            os.rename(output_path, temp_output)

            import subprocess

            # Check if background music exists
            music_path = self.base_dir / self.config.get("music_path", "data/audio/music/Frolic-Es-Jammy-Jams.mp3")
            music_volume = self.config.get("music_volume", 0.15)
            narration_volume = self.config.get("narration_volume", 1.0)

            if music_path.exists():
                log(f"Mixing background music: {music_path} at volume {music_volume}")
                # SIMPLIFIED approach: use -stream_loop and -t to avoid infinite loop issues
                # -stream_loop -1: loop the music input
                # -t {duration}: limit output to narration duration
                # This avoids the complex aloop filter that was causing timeouts
                filter_complex = (
                    f"[1:a]volume={narration_volume}[narration];"
                    f"[2:a]volume={music_volume}[music];"
                    f"[narration][music]amix=inputs=2:duration=first[aout]"
                )

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_output,
                    "-i", audio_path,
                    "-stream_loop", "-1",  # Loop music infinitely
                    "-i", str(music_path),
                    "-t", str(audio_duration + 1),  # Limit to audio duration + 1 sec buffer
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", self.config["audio_bitrate"],
                    "-shortest",
                    output_path
                ]
            else:
                log(f"Background music not found at {music_path}, using narration only", "WARN")
                # Fallback: just mux narration without music
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

            # Use Popen for better control on Windows
            # CREATE_NO_WINDOW prevents the FFmpeg console window from appearing
            import sys
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            try:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=creation_flags
                )

                # Wait with timeout (600 seconds = 10 minutes)
                stdout, stderr = process.communicate(timeout=600)
                returncode = process.returncode
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""

            except subprocess.TimeoutExpired:
                log("FFmpeg timeout - killing process", "ERROR")
                process.kill()
                process.wait()
                # Fallback: keep video without audio
                os.rename(temp_output, output_path)
                return {
                    "status": "partial",
                    "message": "Video created but audio muxing timed out (10 min limit)",
                    "output_path": output_path,
                    "error": "FFmpeg timeout after 600 seconds"
                }

            if returncode != 0:
                log(f"FFmpeg FAILED: {stderr_text}", "ERROR")
                # Fallback: keep video without audio
                os.rename(temp_output, output_path)
                return {
                    "status": "partial",
                    "message": "Video created but audio muxing failed",
                    "output_path": output_path,
                    "error": stderr_text
                }

            # Clean up temp file
            if os.path.exists(temp_output):
                os.remove(temp_output)
                log("Temp file cleaned up")

            log("=" * 50)
            log(f"RENDER COMPLETE: {output_path}")
            log(f"Poses used: {poses_used}")
            log("=" * 50)

            update_render_status("complete", f"Video rendered successfully!", 100, {
                "output_path": output_path,
                "duration": audio_duration,
                "frames": total_frames
            })

            return {
                "status": "success",
                "output_path": output_path,
                "duration": audio_duration,
                "frames": total_frames,
                "poses_used": list(poses_used)
            }

        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            log(f"RENDER EXCEPTION: {str(e)}", "ERROR")
            log(f"Traceback:\n{error_tb}", "ERROR")
            update_render_status("error", f"Render failed: {str(e)}", 0, {"error": str(e)})
            # Ensure container is closed on error to avoid file handle leaks
            if output_container is not None:
                try:
                    output_container.close()
                    log("Output container closed after error")
                except Exception:
                    pass
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
