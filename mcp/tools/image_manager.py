"""
Image Manager for Manual Image Upload and Ordering
Handles image registration and intelligent ordering based on script content.
"""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class ImageManager:
    """Manages manually uploaded images for video assembly."""

    def __init__(self, images_dir: Path):
        """Initialize the image manager.

        Args:
            images_dir: Directory where images are stored
        """
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.images_dir / "image_registry.json"
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """Load the image registry from disk."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {"images": [], "scripts": {}}

    def _save_registry(self):
        """Save the image registry to disk."""
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)

    async def register_images(
        self,
        image_descriptions: list[dict],
        script_id: Optional[str] = None
    ) -> dict:
        """
        Register manually uploaded images for video assembly.

        Args:
            image_descriptions: List of {"filename": str, "description": str}
            script_id: Optional script ID to associate images with

        Returns:
            dict: Registration results with suggested ordering
        """
        registered = []
        not_found = []

        for img_desc in image_descriptions:
            filename = img_desc.get("filename", "")
            description = img_desc.get("description", "")

            # Check if file exists
            img_path = self.images_dir / filename
            if img_path.exists():
                img_entry = {
                    "id": f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(registered)}",
                    "filename": filename,
                    "path": str(img_path),
                    "description": description,
                    "script_id": script_id,
                    "registered_at": datetime.now().isoformat(),
                    "suggested_placement": None
                }
                registered.append(img_entry)
                self.registry["images"].append(img_entry)
            else:
                not_found.append({
                    "filename": filename,
                    "expected_path": str(img_path),
                    "instruction": f"Please place the image at: {img_path}"
                })

        # Associate with script if provided
        if script_id:
            if script_id not in self.registry["scripts"]:
                self.registry["scripts"][script_id] = []
            self.registry["scripts"][script_id].extend(
                [img["id"] for img in registered]
            )

        self._save_registry()

        result = {
            "status": "success" if registered else "no_images_found",
            "registered_count": len(registered),
            "registered_images": registered,
            "not_found": not_found,
            "images_directory": str(self.images_dir),
            "instructions": """
Images have been registered. To use them in your video:

1. The images will be available for the render_short tool
2. Claude will intelligently order them based on:
   - Image descriptions
   - Script dialogue content
   - Visual flow and pacing

3. You can manually specify order by providing placement hints in descriptions:
   - "opening" - Use as the first frame
   - "closing" - Use as the last frame
   - "line_X" - Use during dialogue line X
"""
        }

        if not_found:
            result["action_required"] = f"""
The following images were not found. Please:
1. Place them in: {self.images_dir}
2. Run upload_images again to register them

Alternatively, drag and drop images in the Claude Desktop chat.
"""

        return result

    async def suggest_ordering(
        self,
        script_id: str,
        script_content: dict
    ) -> dict:
        """
        Suggest intelligent ordering of images based on script content.

        Args:
            script_id: Script ID
            script_content: The script JSON with dialogue

        Returns:
            dict: Suggested ordering with reasoning
        """
        # Get images for this script
        script_images = self.registry["scripts"].get(script_id, [])
        if not script_images:
            return {
                "status": "no_images",
                "message": "No images registered for this script"
            }

        # Get full image entries
        images = [
            img for img in self.registry["images"]
            if img["id"] in script_images
        ]

        dialogue = script_content.get("script", {}).get("dialogue", [])

        # Build suggestions based on descriptions and dialogue
        suggestions = []
        opening_image = None
        closing_image = None

        for img in images:
            desc_lower = img["description"].lower()

            # Check for explicit placement hints
            if "opening" in desc_lower or "first" in desc_lower or "start" in desc_lower:
                opening_image = img
                continue
            if "closing" in desc_lower or "last" in desc_lower or "end" in desc_lower:
                closing_image = img
                continue

            # Match to dialogue based on keywords
            best_match_idx = 0
            best_match_score = 0

            for idx, line in enumerate(dialogue):
                text_lower = line.get("text", "").lower()
                # Simple keyword matching
                words = desc_lower.split()
                score = sum(1 for word in words if word in text_lower and len(word) > 3)
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = idx

            suggestions.append({
                "image": img,
                "suggested_dialogue_index": best_match_idx,
                "confidence": "high" if best_match_score > 2 else "medium" if best_match_score > 0 else "low",
                "reasoning": f"Matched based on {best_match_score} keyword(s) in dialogue"
            })

        # Sort suggestions by dialogue index
        suggestions.sort(key=lambda x: x["suggested_dialogue_index"])

        # Build final ordering
        ordered = []
        if opening_image:
            ordered.append({
                "image": opening_image,
                "placement": "opening",
                "timing": "0.0s - 2.0s"
            })

        for sug in suggestions:
            ordered.append({
                "image": sug["image"],
                "placement": f"dialogue_line_{sug['suggested_dialogue_index']}",
                "confidence": sug["confidence"]
            })

        if closing_image:
            ordered.append({
                "image": closing_image,
                "placement": "closing",
                "timing": "last 2 seconds"
            })

        return {
            "status": "success",
            "script_id": script_id,
            "total_images": len(images),
            "suggested_order": ordered,
            "instructions": """
Review the suggested ordering above. You can:
1. Approve this ordering for render_short
2. Ask Claude to adjust specific placements
3. Manually specify a different order

To use custom ordering, pass the order to render_short as:
{
    "image_order": ["img_id_1", "img_id_2", ...]
}
"""
        }

    def get_script_images(self, script_id: str) -> list[dict]:
        """Get all images associated with a script."""
        image_ids = self.registry["scripts"].get(script_id, [])
        return [
            img for img in self.registry["images"]
            if img["id"] in image_ids
        ]

    def list_all_images(self) -> list[dict]:
        """List all registered images."""
        return self.registry["images"]
