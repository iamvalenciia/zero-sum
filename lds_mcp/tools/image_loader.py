"""
Centralized Image Loading System for Zero-Sum Video Production

This module provides a standardized way to load character images for video rendering.
It reads from images_catalog.json and provides lip-sync support (open/closed mouth).

STANDARD POSE IDS:
- analyst_close  : Close-up of Analyst (testimony, whispers)
- analyst_front  : Medium shot of Analyst (teaching, explaining)
- analyst_pov    : POV shot from Skeptic's perspective
- skeptic_close  : Close-up of Skeptic (realization, emotion)
- skeptic_front  : Medium shot of Skeptic (asking questions)
- skeptic_side   : Side profile of Skeptic (thinking, reflecting)

Usage:
    loader = ImageLoader(base_dir)
    image = loader.get_image("analyst_front", mouth_open=True)
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from PIL import Image


@dataclass
class PoseImage:
    """Represents a single pose with open/closed mouth variants."""
    pose_id: str
    character: str  # "analyst" or "skeptic"
    description: str
    closed_path: Path
    open_path: Path
    _closed_image: Optional[Image.Image] = field(default=None, repr=False)
    _open_image: Optional[Image.Image] = field(default=None, repr=False)

    def get_image(self, mouth_open: bool = False) -> Optional[Image.Image]:
        """Get the image for this pose with specified mouth state."""
        if mouth_open:
            if self._open_image is None:
                self._open_image = self._load_image(self.open_path)
            return self._open_image
        else:
            if self._closed_image is None:
                self._closed_image = self._load_image(self.closed_path)
            return self._closed_image

    def _load_image(self, path: Path) -> Optional[Image.Image]:
        """Load and convert image to RGBA."""
        if not path.exists():
            return None
        try:
            return Image.open(path).convert("RGBA")
        except Exception as e:
            print(f"[ImageLoader] Error loading {path}: {e}")
            return None

    def preload(self):
        """Preload both image variants into memory."""
        self._closed_image = self._load_image(self.closed_path)
        self._open_image = self._load_image(self.open_path)


@dataclass
class CharacterConfig:
    """Configuration for a character."""
    name: str  # Display name: "Analyst" or "Skeptic"
    key: str   # Internal key: "analyst" or "skeptic"
    poses: List[str]  # Available pose IDs
    default_pose: str  # Default pose for this character


# Standard character configurations
STANDARD_CHARACTERS: Dict[str, CharacterConfig] = {
    "analyst": CharacterConfig(
        name="Analyst",
        key="analyst",
        poses=["analyst_close", "analyst_front", "analyst_pov"],
        default_pose="analyst_front"
    ),
    "skeptic": CharacterConfig(
        name="Skeptic",
        key="skeptic",
        poses=["skeptic_close", "skeptic_front", "skeptic_side"],
        default_pose="skeptic_front"
    )
}

# Aliases for backward compatibility
CHARACTER_ALIASES: Dict[str, str] = {
    "Sister Faith": "analyst",
    "sister_faith": "analyst",
    "Brother Marcus": "skeptic",
    "brother_marcus": "skeptic",
    "Analyst": "analyst",
    "Skeptic": "skeptic"
}


class ImageLoader:
    """
    Centralized image loader that reads from images_catalog.json.

    This is the SINGLE SOURCE OF TRUTH for character images in the project.
    All rendering code should use this loader instead of direct file access.
    """

    CATALOG_FILENAME = "images_catalog.json"

    # Supported image extensions - will try alternatives if primary doesn't exist
    SUPPORTED_EXTENSIONS = [".jpeg", ".jpg", ".png", ".webp"]

    def __init__(self, base_dir: Path, preload: bool = False):
        """
        Initialize the image loader.

        Args:
            base_dir: Project base directory (contains data/ folder)
            preload: If True, load all images into memory immediately
        """
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "data" / "images"
        self.catalog_path = self.images_dir / self.CATALOG_FILENAME

        self._poses: Dict[str, PoseImage] = {}
        self._characters = STANDARD_CHARACTERS.copy()
        self._loaded = False

        # Load catalog
        self._load_catalog()

        if preload:
            self.preload_all()

    def _load_catalog(self) -> None:
        """Load the images catalog from JSON."""
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                f"Images catalog not found: {self.catalog_path}\n"
                f"Please create {self.CATALOG_FILENAME} in {self.images_dir}"
            )

        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            catalog_data = json.load(f)

        for entry in catalog_data:
            pose_id = entry["id"]
            character = entry["character"].lower()

            # Resolve paths relative to base_dir
            closed_path = self.base_dir / entry["closed"]["path"]
            open_path = self.base_dir / entry["open"]["path"]

            # Try alternative extensions if file doesn't exist
            closed_path = self._find_with_alt_extension(closed_path)
            open_path = self._find_with_alt_extension(open_path)

            self._poses[pose_id] = PoseImage(
                pose_id=pose_id,
                character=character,
                description=entry.get("description", ""),
                closed_path=closed_path,
                open_path=open_path
            )

        self._loaded = True

    def _find_with_alt_extension(self, path: Path) -> Path:
        """
        Find a file with alternative extension if the original doesn't exist.

        This handles cases where catalog says .png but file is .jpeg, etc.
        """
        if path.exists():
            return path

        # Try each supported extension
        stem = path.stem
        parent = path.parent

        for ext in self.SUPPORTED_EXTENSIONS:
            alt_path = parent / f"{stem}{ext}"
            if alt_path.exists():
                return alt_path

        # Return original path (will fail gracefully later)
        return path

    def get_image(
        self,
        pose_id: str,
        mouth_open: bool = False
    ) -> Optional[Image.Image]:
        """
        Get an image for a specific pose.

        Args:
            pose_id: The pose identifier (e.g., "analyst_front")
            mouth_open: If True, return open mouth variant for lip-sync

        Returns:
            PIL Image or None if not found
        """
        pose = self._poses.get(pose_id)
        if pose is None:
            print(f"[ImageLoader] Pose not found: {pose_id}")
            return None
        return pose.get_image(mouth_open)

    def get_character_image(
        self,
        character: str,
        pose_type: str = "front",
        mouth_open: bool = False
    ) -> Optional[Image.Image]:
        """
        Get an image by character name and pose type.

        Args:
            character: Character name or alias (e.g., "Analyst", "Sister Faith")
            pose_type: Pose type (e.g., "close", "front", "side", "pov")
            mouth_open: If True, return open mouth variant

        Returns:
            PIL Image or None if not found
        """
        # Resolve character alias
        char_key = CHARACTER_ALIASES.get(character, character.lower())

        # Build pose_id
        pose_id = f"{char_key}_{pose_type}"

        return self.get_image(pose_id, mouth_open)

    def get_default_image(
        self,
        character: str,
        mouth_open: bool = False
    ) -> Optional[Image.Image]:
        """
        Get the default pose image for a character.

        Args:
            character: Character name or alias
            mouth_open: If True, return open mouth variant

        Returns:
            PIL Image or None if not found
        """
        char_key = CHARACTER_ALIASES.get(character, character.lower())
        char_config = self._characters.get(char_key)

        if char_config is None:
            print(f"[ImageLoader] Unknown character: {character}")
            return None

        return self.get_image(char_config.default_pose, mouth_open)

    def get_pose(self, pose_id: str) -> Optional[PoseImage]:
        """Get the PoseImage object for direct access."""
        return self._poses.get(pose_id)

    def get_poses_for_character(self, character: str) -> List[str]:
        """Get all available pose IDs for a character."""
        char_key = CHARACTER_ALIASES.get(character, character.lower())
        return [
            pose_id for pose_id, pose in self._poses.items()
            if pose.character == char_key
        ]

    def preload_all(self) -> None:
        """Preload all images into memory for faster rendering."""
        for pose in self._poses.values():
            pose.preload()

    def validate_catalog(self) -> Dict[str, Any]:
        """
        Validate that all images in the catalog exist and are loadable.

        Returns:
            Dict with validation results
        """
        results = {
            "valid": True,
            "total_poses": len(self._poses),
            "missing_files": [],
            "load_errors": [],
            "poses": {}
        }

        for pose_id, pose in self._poses.items():
            pose_result = {
                "closed_exists": pose.closed_path.exists(),
                "open_exists": pose.open_path.exists(),
                "closed_loadable": False,
                "open_loadable": False
            }

            if not pose.closed_path.exists():
                results["missing_files"].append(str(pose.closed_path))
                results["valid"] = False
            else:
                try:
                    img = Image.open(pose.closed_path)
                    img.verify()
                    pose_result["closed_loadable"] = True
                except Exception as e:
                    results["load_errors"].append(f"{pose.closed_path}: {e}")
                    results["valid"] = False

            if not pose.open_path.exists():
                results["missing_files"].append(str(pose.open_path))
                results["valid"] = False
            else:
                try:
                    img = Image.open(pose.open_path)
                    img.verify()
                    pose_result["open_loadable"] = True
                except Exception as e:
                    results["load_errors"].append(f"{pose.open_path}: {e}")
                    results["valid"] = False

            results["poses"][pose_id] = pose_result

        return results

    def get_catalog_summary(self) -> Dict[str, Any]:
        """Get a summary of the loaded catalog."""
        return {
            "catalog_path": str(self.catalog_path),
            "images_dir": str(self.images_dir),
            "total_poses": len(self._poses),
            "characters": {
                char_key: {
                    "name": config.name,
                    "poses": config.poses,
                    "default_pose": config.default_pose
                }
                for char_key, config in self._characters.items()
            },
            "available_poses": list(self._poses.keys()),
            "pose_details": {
                pose_id: {
                    "character": pose.character,
                    "description": pose.description[:50] + "..." if len(pose.description) > 50 else pose.description
                }
                for pose_id, pose in self._poses.items()
            }
        }


# Singleton instance for global access
_global_loader: Optional[ImageLoader] = None


def get_image_loader(base_dir: Optional[Path] = None) -> ImageLoader:
    """
    Get the global ImageLoader instance.

    Args:
        base_dir: Project base directory (only needed on first call)

    Returns:
        ImageLoader instance
    """
    global _global_loader

    if _global_loader is None:
        if base_dir is None:
            # Default to parent of lds_mcp directory
            base_dir = Path(__file__).parent.parent.parent
        _global_loader = ImageLoader(base_dir)

    return _global_loader


def reset_image_loader() -> None:
    """Reset the global loader (useful for testing)."""
    global _global_loader
    _global_loader = None


# Standard pose information for script generation
STANDARD_POSES = {
    "analyst_close": {
        "character": "Analyst",
        "type": "close",
        "description": "Close-up portrait. Use for: testimony, profound truths, whispers, emotional moments.",
        "when_to_use": ["[softly]", "[whispers]", "[reverently]", "testimony", "sacred"]
    },
    "analyst_front": {
        "character": "Analyst",
        "type": "front",
        "description": "Medium shot facing viewer. Use for: standard teaching, explaining doctrine, neutral delivery.",
        "when_to_use": ["[warmly]", "explaining", "teaching", "default"]
    },
    "analyst_pov": {
        "character": "Analyst",
        "type": "pov",
        "description": "POV shot from Skeptic's perspective. Use for: when being asked a question, listening.",
        "when_to_use": ["listening", "responding to question", "thoughtful pause"]
    },
    "skeptic_close": {
        "character": "Skeptic",
        "type": "close",
        "description": "Close-up portrait. Use for: realization, strong emotion, confusion, nervous laughter.",
        "when_to_use": ["[realizing]", "[surprised]", "moment of understanding", "emotional"]
    },
    "skeptic_front": {
        "character": "Skeptic",
        "type": "front",
        "description": "Medium shot facing viewer. Use for: asking questions, listening, general inquiries.",
        "when_to_use": ["[curious]", "asking", "questioning", "default"]
    },
    "skeptic_side": {
        "character": "Skeptic",
        "type": "side",
        "description": "Side profile. Use for: thinking, reflecting, hesitation, avoiding eye contact.",
        "when_to_use": ["[thoughtfully]", "[pondering]", "reflecting", "hesitation"]
    }
}


def get_pose_for_emotion(character: str, emotion_tag: str) -> str:
    """
    Suggest the best pose based on character and emotion tag.

    Args:
        character: "Analyst" or "Skeptic"
        emotion_tag: ElevenLabs emotion tag like "[softly]"

    Returns:
        Recommended pose_id
    """
    char_key = CHARACTER_ALIASES.get(character, character.lower())
    emotion_lower = emotion_tag.lower().strip("[]")

    # Check each pose's when_to_use list
    for pose_id, pose_info in STANDARD_POSES.items():
        if pose_info["character"].lower() != char_key:
            continue

        for trigger in pose_info["when_to_use"]:
            if emotion_lower in trigger.lower() or trigger.lower() in emotion_lower:
                return pose_id

    # Return default pose for character
    return STANDARD_CHARACTERS[char_key].default_pose
