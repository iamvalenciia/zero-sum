"""
Unified Project Manager for LDS Video Creation Pipeline.
Centralizes all path management and project state tracking.

This module ensures consistency between MCP tools and CLI handlers,
eliminating the manual file management that was previously required.
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ProjectPaths:
    """All paths for a project, computed from project_id."""
    project_id: str
    base_dir: Path

    # Computed paths
    script_file: Path = field(init=False)
    audio_file: Path = field(init=False)
    timestamps_file: Path = field(init=False)
    images_dir: Path = field(init=False)
    output_file: Path = field(init=False)
    video_script_file: Path = field(init=False)

    def __post_init__(self):
        shorts_dir = self.base_dir / "data" / "shorts"
        self.script_file = shorts_dir / "scripts" / f"{self.project_id}.json"
        self.audio_file = shorts_dir / "audio" / f"{self.project_id}.mp3"
        self.timestamps_file = shorts_dir / "audio" / f"{self.project_id}_timestamps.json"
        self.images_dir = shorts_dir / "images" / self.project_id
        self.output_file = shorts_dir / "output" / f"{self.project_id}.mp4"
        self.video_script_file = shorts_dir / "scripts" / f"{self.project_id}_video_script.json"

        # Also create legacy symlink paths for CLI compatibility
        self.legacy_audio = self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue.mp3"
        self.legacy_timestamps = self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue_timestamps.json"
        self.legacy_production_plan = self.base_dir / "data" / "production_plan.json"


class ProjectManager:
    """
    Manages video project lifecycle with unified path handling.

    Responsibilities:
    - Generate unique project IDs
    - Track project state (script, audio, timestamps, images, video)
    - Provide consistent paths across MCP and CLI
    - Auto-create required directories
    - Handle legacy path compatibility
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            # Default to repository root
            base_dir = Path(__file__).parent.parent.parent
        self.base_dir = Path(base_dir)
        self.shorts_dir = self.base_dir / "data" / "shorts"
        self._ensure_directories()

        # Track current active project
        self._current_project_id: Optional[str] = None
        self._state_file = self.shorts_dir / ".project_state.json"
        self._load_state()

    def _ensure_directories(self):
        """Create all required directories."""
        dirs = [
            self.shorts_dir / "scripts",
            self.shorts_dir / "audio",
            self.shorts_dir / "images",
            self.shorts_dir / "output",
            self.base_dir / "data" / "audio" / "elevenlabs",  # Legacy
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_state(self):
        """Load persistent state."""
        if self._state_file.exists():
            try:
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                    self._current_project_id = state.get("current_project_id")
            except:
                self._current_project_id = None

    def _save_state(self):
        """Persist current state."""
        state = {"current_project_id": self._current_project_id}
        with open(self._state_file, 'w') as f:
            json.dump(state, f)

    def generate_project_id(self, prefix: str = "lds") -> str:
        """Generate a unique project ID with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Add random suffix to avoid collisions
        import secrets
        suffix = secrets.token_hex(3)
        return f"{prefix}_{timestamp}_{suffix}"

    def set_current_project(self, project_id: str):
        """Set the current active project."""
        self._current_project_id = project_id
        self._save_state()

    def get_current_project(self) -> Optional[str]:
        """Get the current active project ID."""
        return self._current_project_id

    def get_paths(self, project_id: Optional[str] = None) -> ProjectPaths:
        """Get all paths for a project."""
        pid = project_id or self._current_project_id
        if not pid:
            raise ValueError("No project ID specified and no current project set")
        return ProjectPaths(project_id=pid, base_dir=self.base_dir)

    def get_project_status(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed status of a project."""
        paths = self.get_paths(project_id)

        status = {
            "project_id": paths.project_id,
            "exists": {
                "script": paths.script_file.exists(),
                "audio": paths.audio_file.exists(),
                "timestamps": paths.timestamps_file.exists(),
                "video": paths.output_file.exists(),
            },
            "paths": {
                "script": str(paths.script_file),
                "audio": str(paths.audio_file),
                "timestamps": str(paths.timestamps_file),
                "output": str(paths.output_file),
            },
            "images": [],
            "ready_for_render": False
        }

        # Check images
        if paths.images_dir.exists():
            status["images"] = [f.name for f in paths.images_dir.iterdir() if f.is_file()]

        # Check if ready to render
        status["ready_for_render"] = all([
            status["exists"]["script"],
            status["exists"]["audio"],
            status["exists"]["timestamps"]
        ])

        return status

    def save_script(self, script_data: Dict, project_id: Optional[str] = None) -> str:
        """
        Save a script and set it as current project.
        Returns the project_id.
        """
        # Extract or generate project ID
        script_content = script_data.get("script", script_data)
        pid = project_id or script_content.get("id") or self.generate_project_id()

        # Ensure script has the ID
        if "script" in script_data:
            script_data["script"]["id"] = pid
        else:
            script_data["id"] = pid

        paths = ProjectPaths(project_id=pid, base_dir=self.base_dir)

        # Ensure directory exists
        paths.script_file.parent.mkdir(parents=True, exist_ok=True)

        # Save script
        with open(paths.script_file, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        # Also save to legacy location for CLI compatibility
        with open(paths.legacy_production_plan, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        # Set as current project
        self.set_current_project(pid)

        return pid

    def load_script(self, project_id: Optional[str] = None) -> Optional[Dict]:
        """Load a script by project ID."""
        paths = self.get_paths(project_id)

        if paths.script_file.exists():
            with open(paths.script_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_audio(self, audio_bytes: bytes, project_id: Optional[str] = None) -> str:
        """Save audio file and create legacy symlink."""
        paths = self.get_paths(project_id)

        # Ensure directory exists
        paths.audio_file.parent.mkdir(parents=True, exist_ok=True)

        # Save audio
        with open(paths.audio_file, 'wb') as f:
            f.write(audio_bytes)

        # Create/update legacy symlink or copy for CLI compatibility
        paths.legacy_audio.parent.mkdir(parents=True, exist_ok=True)
        if paths.legacy_audio.exists() or paths.legacy_audio.is_symlink():
            paths.legacy_audio.unlink()

        # Use copy instead of symlink for Windows compatibility
        shutil.copy2(paths.audio_file, paths.legacy_audio)

        return str(paths.audio_file)

    def save_timestamps(self, timestamps_data: Dict, project_id: Optional[str] = None) -> str:
        """Save timestamps and create legacy copy."""
        paths = self.get_paths(project_id)

        # Ensure directory exists
        paths.timestamps_file.parent.mkdir(parents=True, exist_ok=True)

        # Save timestamps
        with open(paths.timestamps_file, 'w', encoding='utf-8') as f:
            json.dump(timestamps_data, f, indent=2, ensure_ascii=False)

        # Create legacy copy
        with open(paths.legacy_timestamps, 'w', encoding='utf-8') as f:
            json.dump(timestamps_data, f, indent=2, ensure_ascii=False)

        return str(paths.timestamps_file)

    def register_image(
        self,
        source_path: str,
        filename: Optional[str] = None,
        project_id: Optional[str] = None,
        copy: bool = True
    ) -> str:
        """
        Register an image for the project.

        Args:
            source_path: Path to the source image
            filename: Optional new filename (keeps original if not specified)
            project_id: Project ID (uses current if not specified)
            copy: If True, copy file; if False, move it

        Returns:
            Path to the registered image
        """
        paths = self.get_paths(project_id)
        source = Path(source_path)

        if not source.exists():
            raise FileNotFoundError(f"Source image not found: {source_path}")

        # Determine destination filename
        dest_filename = filename or source.name
        dest_path = paths.images_dir / dest_filename

        # Ensure directory exists
        paths.images_dir.mkdir(parents=True, exist_ok=True)

        # Copy or move
        if copy:
            shutil.copy2(source, dest_path)
        else:
            shutil.move(str(source), str(dest_path))

        return str(dest_path)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects with their status."""
        scripts_dir = self.shorts_dir / "scripts"
        projects = []

        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.json"):
                # Skip video script files
                if script_file.stem.endswith("_video_script"):
                    continue

                project_id = script_file.stem
                try:
                    status = self.get_project_status(project_id)
                    projects.append({
                        "id": project_id,
                        "is_current": project_id == self._current_project_id,
                        **status["exists"]
                    })
                except:
                    projects.append({
                        "id": project_id,
                        "is_current": project_id == self._current_project_id,
                        "error": "Could not read status"
                    })

        return projects

    def cleanup_project(self, project_id: str, archive: bool = True) -> Dict[str, Any]:
        """
        Clean up a project's files.

        Args:
            project_id: Project to clean up
            archive: If True, move to archive; if False, delete

        Returns:
            Summary of cleaned files
        """
        paths = self.get_paths(project_id)
        cleaned = {"archived": [], "deleted": [], "errors": []}

        if archive:
            archive_dir = self.base_dir / "old-videos" / project_id
            archive_dir.mkdir(parents=True, exist_ok=True)

        files_to_process = [
            paths.script_file,
            paths.audio_file,
            paths.timestamps_file,
            paths.output_file,
            paths.video_script_file,
        ]

        for file_path in files_to_process:
            if file_path.exists():
                try:
                    if archive:
                        shutil.move(str(file_path), str(archive_dir / file_path.name))
                        cleaned["archived"].append(str(file_path))
                    else:
                        file_path.unlink()
                        cleaned["deleted"].append(str(file_path))
                except Exception as e:
                    cleaned["errors"].append(f"{file_path}: {e}")

        # Handle images directory
        if paths.images_dir.exists():
            try:
                if archive:
                    shutil.move(str(paths.images_dir), str(archive_dir / "images"))
                else:
                    shutil.rmtree(paths.images_dir)
                cleaned["archived" if archive else "deleted"].append(str(paths.images_dir))
            except Exception as e:
                cleaned["errors"].append(f"{paths.images_dir}: {e}")

        # Clear current project if it was this one
        if self._current_project_id == project_id:
            self._current_project_id = None
            self._save_state()

        return cleaned


# Singleton instance for easy access
_manager_instance: Optional[ProjectManager] = None


def get_project_manager(base_dir: Optional[Path] = None) -> ProjectManager:
    """Get or create the singleton ProjectManager instance."""
    global _manager_instance
    if _manager_instance is None or (base_dir and _manager_instance.base_dir != base_dir):
        _manager_instance = ProjectManager(base_dir)
    return _manager_instance
