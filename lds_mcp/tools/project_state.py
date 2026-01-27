"""
Project State Manager for Zero-Sum Video Production Pipeline.

This module provides a comprehensive state management system that:
1. Tracks the current phase of video production
2. Manages project lifecycle (create, archive, cleanup)
3. Provides clear guidance on next steps
4. Prevents conflicts between projects

PHASES:
1. IDLE - No active project, ready to start
2. IDEA - Brainstorming topic and context
3. SCRIPT - Creating/editing the dialogue script
4. AUDIO - Generating audio from script
5. IMAGES - Managing visual assets (optional)
6. RENDER - Rendering the final video
7. COMPLETE - Video finished, ready for export/archive
8. ARCHIVED - Project moved to archive folder
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class ProjectPhase(Enum):
    """Phases of the video production pipeline."""
    IDLE = "idle"           # No active project
    IDEA = "idea"           # Brainstorming/planning
    SCRIPT = "script"       # Creating dialogue script
    AUDIO = "audio"         # Generating audio
    IMAGES = "images"       # Managing images (optional)
    RENDER = "render"       # Rendering video
    COMPLETE = "complete"   # Video finished
    ARCHIVED = "archived"   # Moved to archive


# Phase descriptions for user guidance
PHASE_INFO = {
    ProjectPhase.IDLE: {
        "name": "No Active Project",
        "description": "Ready to start a new video project.",
        "next_actions": ["Create a new project with a topic"],
        "emoji": "[NEW]"
    },
    ProjectPhase.IDEA: {
        "name": "Idea & Planning",
        "description": "Brainstorming the video topic and gathering context.",
        "next_actions": [
            "Search for scriptures or prophet quotes",
            "Define the hook question",
            "Move to script creation"
        ],
        "emoji": "[IDEA]"
    },
    ProjectPhase.SCRIPT: {
        "name": "Script Creation",
        "description": "Writing the dialogue between Analyst and Skeptic.",
        "next_actions": [
            "Generate or refine the dialogue JSON",
            "Validate character names and emotion tags",
            "Save the script with finalize_script"
        ],
        "emoji": "[SCRIPT]"
    },
    ProjectPhase.AUDIO: {
        "name": "Audio Generation",
        "description": "Creating the voice narration with ElevenLabs.",
        "next_actions": [
            "Generate audio with generate_audio",
            "Wait for audio processing",
            "Proceed to rendering or add images"
        ],
        "emoji": "[AUDIO]"
    },
    ProjectPhase.IMAGES: {
        "name": "Image Management",
        "description": "Adding visual assets for the video (optional).",
        "next_actions": [
            "Upload custom images if needed",
            "Character poses are automatic",
            "Proceed to rendering"
        ],
        "emoji": "[IMAGES]"
    },
    ProjectPhase.RENDER: {
        "name": "Video Rendering",
        "description": "Creating the final video with lip-sync and captions.",
        "next_actions": [
            "Execute render with execute_render",
            "Wait for video processing",
            "Review the output"
        ],
        "emoji": "[RENDER]"
    },
    ProjectPhase.COMPLETE: {
        "name": "Video Complete",
        "description": "Video is ready! You can review or archive the project.",
        "next_actions": [
            "Watch the video in data/shorts/output/",
            "Archive the project to start fresh",
            "Make adjustments if needed"
        ],
        "emoji": "[DONE]"
    },
    ProjectPhase.ARCHIVED: {
        "name": "Archived",
        "description": "Project has been moved to the archive folder.",
        "next_actions": ["Start a new project"],
        "emoji": "[ARCHIVED]"
    }
}


@dataclass
class ProjectState:
    """Represents the current state of a project."""
    project_id: Optional[str] = None
    phase: ProjectPhase = ProjectPhase.IDLE
    topic: str = ""
    hook_text: str = ""
    created_at: Optional[str] = None
    last_updated: Optional[str] = None

    # File existence flags
    has_script: bool = False
    has_audio: bool = False
    has_timestamps: bool = False
    has_video: bool = False

    # Metadata
    dialogue_count: int = 0
    audio_duration: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["phase"] = self.phase.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectState":
        """Create from dictionary."""
        data["phase"] = ProjectPhase(data.get("phase", "idle"))
        return cls(**data)


class ProjectStateManager:
    """
    Manages project state and lifecycle for the video production pipeline.

    This is the SINGLE SOURCE OF TRUTH for project status.
    All tools should consult this manager to understand current state.
    """

    STATE_FILE = ".project_state.json"
    ARCHIVE_DIR = "old-videos"

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent
        self.base_dir = Path(base_dir)
        self.state_file = self.base_dir / "data" / self.STATE_FILE
        self.shorts_dir = self.base_dir / "data" / "shorts"
        self.archive_dir = self.base_dir / self.ARCHIVE_DIR

        # Ensure directories exist
        self.shorts_dir.mkdir(parents=True, exist_ok=True)

        # Load or create state
        self._state = self._load_state()

    def _load_state(self) -> ProjectState:
        """Load state from file or create new."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ProjectState.from_dict(data)
            except Exception:
                return ProjectState()
        return ProjectState()

    def _save_state(self) -> None:
        """Save state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self._state.to_dict(), f, indent=2)

    def _update_timestamp(self) -> None:
        """Update the last_updated timestamp."""
        self._state.last_updated = datetime.now().isoformat()

    def _detect_phase(self) -> ProjectPhase:
        """Auto-detect the current phase based on existing files."""
        if not self._state.project_id:
            return ProjectPhase.IDLE

        # Check file existence
        pid = self._state.project_id
        script_path = self.shorts_dir / "scripts" / f"{pid}.json"
        audio_path = self.shorts_dir / "audio" / f"{pid}.mp3"
        timestamps_path = self.shorts_dir / "audio" / f"{pid}_timestamps.json"
        video_path = self.shorts_dir / "output" / f"{pid}.mp4"

        self._state.has_script = script_path.exists()
        self._state.has_audio = audio_path.exists()
        self._state.has_timestamps = timestamps_path.exists()
        self._state.has_video = video_path.exists()

        # Determine phase
        if self._state.has_video:
            return ProjectPhase.COMPLETE
        elif self._state.has_audio:
            return ProjectPhase.RENDER
        elif self._state.has_script:
            return ProjectPhase.AUDIO
        elif self._state.topic:
            return ProjectPhase.SCRIPT
        else:
            return ProjectPhase.IDEA

    def refresh_state(self) -> ProjectState:
        """Refresh state by checking actual files."""
        if self._state.project_id:
            self._state.phase = self._detect_phase()
            self._save_state()
        return self._state

    def get_state(self) -> ProjectState:
        """Get current project state."""
        return self.refresh_state()

    def get_status_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive status report for the current project.
        This is the main method to call when opening a new chat.
        """
        state = self.refresh_state()
        phase_info = PHASE_INFO[state.phase]

        report = {
            "current_phase": {
                "id": state.phase.value,
                "name": phase_info["name"],
                "emoji": phase_info["emoji"],
                "description": phase_info["description"]
            },
            "project": {
                "id": state.project_id,
                "topic": state.topic,
                "hook_text": state.hook_text,
                "created_at": state.created_at
            },
            "files": {
                "script": state.has_script,
                "audio": state.has_audio,
                "timestamps": state.has_timestamps,
                "video": state.has_video
            },
            "next_actions": phase_info["next_actions"],
            "suggestions": []
        }

        # Add contextual suggestions
        if state.phase == ProjectPhase.IDLE:
            report["suggestions"].append({
                "action": "start_new_project",
                "message": "Ready to create a new video! What topic would you like to explore?"
            })
            # Check for leftover files
            if self._has_leftover_files():
                report["suggestions"].append({
                    "action": "cleanup_recommended",
                    "message": "There are files from a previous project. Would you like to archive them first?"
                })

        elif state.phase == ProjectPhase.COMPLETE:
            report["suggestions"].append({
                "action": "archive_project",
                "message": f"Project '{state.project_id}' is complete! Would you like to archive it and start a new one?"
            })
            report["video_path"] = str(self.shorts_dir / "output" / f"{state.project_id}.mp4")

        return report

    def _has_leftover_files(self) -> bool:
        """Check if there are files from a previous project."""
        scripts = list((self.shorts_dir / "scripts").glob("*.json")) if (self.shorts_dir / "scripts").exists() else []
        audio = list((self.shorts_dir / "audio").glob("*.mp3")) if (self.shorts_dir / "audio").exists() else []
        videos = list((self.shorts_dir / "output").glob("*.mp4")) if (self.shorts_dir / "output").exists() else []
        return len(scripts) > 0 or len(audio) > 0 or len(videos) > 0

    def start_new_project(
        self,
        project_id: str,
        topic: str,
        hook_text: str = ""
    ) -> Dict[str, Any]:
        """
        Start a new project, updating state.
        """
        self._state = ProjectState(
            project_id=project_id,
            phase=ProjectPhase.IDEA,
            topic=topic,
            hook_text=hook_text or f"What about {topic}?",
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        self._save_state()

        return {
            "status": "project_started",
            "project_id": project_id,
            "phase": self._state.phase.value,
            "message": f"New project created for topic: {topic}"
        }

    def update_phase(self, phase: ProjectPhase, **kwargs) -> None:
        """Update the current phase and optional metadata."""
        self._state.phase = phase
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._update_timestamp()
        self._save_state()

    def mark_script_saved(self, dialogue_count: int = 0) -> None:
        """Mark that script has been saved."""
        self._state.has_script = True
        self._state.dialogue_count = dialogue_count
        self._state.phase = ProjectPhase.AUDIO
        self._update_timestamp()
        self._save_state()

    def mark_audio_generated(self, duration: float = 0.0) -> None:
        """Mark that audio has been generated."""
        self._state.has_audio = True
        self._state.audio_duration = duration
        self._state.phase = ProjectPhase.RENDER
        self._update_timestamp()
        self._save_state()

    def mark_video_complete(self) -> None:
        """Mark that video has been rendered."""
        self._state.has_video = True
        self._state.phase = ProjectPhase.COMPLETE
        self._update_timestamp()
        self._save_state()

    def archive_current_project(self, delete_after: bool = False) -> Dict[str, Any]:
        """
        Archive the current project to old-videos folder.

        Args:
            delete_after: If True, delete source files after copying

        Returns:
            Archive result with details
        """
        if not self._state.project_id:
            return {
                "status": "error",
                "message": "No active project to archive"
            }

        pid = self._state.project_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{pid}_{timestamp}"
        archive_path = self.archive_dir / archive_name

        # Create archive directory
        archive_path.mkdir(parents=True, exist_ok=True)

        files_archived = []

        # Archive script
        script_src = self.shorts_dir / "scripts" / f"{pid}.json"
        if script_src.exists():
            shutil.copy2(script_src, archive_path / f"{pid}.json")
            files_archived.append(f"scripts/{pid}.json")
            if delete_after:
                script_src.unlink()

        # Archive audio
        audio_src = self.shorts_dir / "audio" / f"{pid}.mp3"
        if audio_src.exists():
            shutil.copy2(audio_src, archive_path / f"{pid}.mp3")
            files_archived.append(f"audio/{pid}.mp3")
            if delete_after:
                audio_src.unlink()

        # Archive timestamps
        ts_src = self.shorts_dir / "audio" / f"{pid}_timestamps.json"
        if ts_src.exists():
            shutil.copy2(ts_src, archive_path / f"{pid}_timestamps.json")
            files_archived.append(f"audio/{pid}_timestamps.json")
            if delete_after:
                ts_src.unlink()

        # Archive video
        video_src = self.shorts_dir / "output" / f"{pid}.mp4"
        if video_src.exists():
            shutil.copy2(video_src, archive_path / f"{pid}.mp4")
            files_archived.append(f"output/{pid}.mp4")
            if delete_after:
                video_src.unlink()

        # Archive images folder if exists
        images_src = self.shorts_dir / "images" / pid
        if images_src.exists():
            shutil.copytree(images_src, archive_path / "images", dirs_exist_ok=True)
            files_archived.append(f"images/{pid}/")
            if delete_after:
                shutil.rmtree(images_src)

        # Save state info to archive
        state_info = {
            "original_project_id": pid,
            "archived_at": datetime.now().isoformat(),
            "topic": self._state.topic,
            "hook_text": self._state.hook_text,
            "files": files_archived
        }
        with open(archive_path / "archive_info.json", "w") as f:
            json.dump(state_info, f, indent=2)

        # Reset state
        self._state = ProjectState()
        self._save_state()

        return {
            "status": "archived",
            "archive_path": str(archive_path),
            "files_archived": files_archived,
            "delete_source": delete_after,
            "message": f"Project '{pid}' archived to {archive_name}",
            "ready_for_new_project": True
        }

    def cleanup_all(self, archive_first: bool = True) -> Dict[str, Any]:
        """
        Clean up all project files to start fresh.

        Args:
            archive_first: If True, archive before deleting

        Returns:
            Cleanup result
        """
        results = []

        # Archive current project if exists
        if archive_first and self._state.project_id:
            archive_result = self.archive_current_project(delete_after=True)
            results.append(archive_result)

        # Clean shorts directories
        for subdir in ["scripts", "audio", "output", "images"]:
            dir_path = self.shorts_dir / subdir
            if dir_path.exists():
                for file in dir_path.iterdir():
                    if file.is_file():
                        file.unlink()
                    elif file.is_dir():
                        shutil.rmtree(file)

        # Reset state
        self._state = ProjectState()
        self._save_state()

        return {
            "status": "cleaned",
            "archive_results": results,
            "message": "All project files cleaned. Ready for a new project!"
        }

    def list_archived_projects(self) -> List[Dict[str, Any]]:
        """List all archived projects."""
        if not self.archive_dir.exists():
            return []

        projects = []
        for item in self.archive_dir.iterdir():
            if item.is_dir():
                info_file = item / "archive_info.json"
                if info_file.exists():
                    with open(info_file) as f:
                        info = json.load(f)
                    projects.append({
                        "folder": item.name,
                        "path": str(item),
                        **info
                    })
                else:
                    projects.append({
                        "folder": item.name,
                        "path": str(item),
                        "topic": "Unknown"
                    })

        return sorted(projects, key=lambda x: x.get("archived_at", ""), reverse=True)


# Singleton instance
_state_manager: Optional[ProjectStateManager] = None


def get_state_manager(base_dir: Optional[Path] = None) -> ProjectStateManager:
    """Get the global ProjectStateManager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ProjectStateManager(base_dir)
    return _state_manager


def reset_state_manager() -> None:
    """Reset the global state manager (for testing)."""
    global _state_manager
    _state_manager = None


# Convenience functions for common operations
def get_welcome_message() -> Dict[str, Any]:
    """
    Get a welcome message with current project status.
    Call this at the start of a new chat session.
    """
    manager = get_state_manager()
    status = manager.get_status_report()

    phase = status["current_phase"]

    # Build welcome message based on state
    if phase["id"] == "idle":
        greeting = f"""
{phase["emoji"]} **Welcome to Zero-Sum Video Creator!**

No active project detected. Ready to create something new!

**What would you like to do?**
1. [NEW] Start a new video project
2. [ARCHIVE] View archived projects
"""
        if status["suggestions"]:
            for s in status["suggestions"]:
                if s["action"] == "cleanup_recommended":
                    greeting += f"\n[!] *Note: {s['message']}*\n"

    elif phase["id"] == "complete":
        project = status["project"]
        greeting = f"""
{phase["emoji"]} **Project Complete!**

Your video for "{project['topic']}" is ready!

[VIDEO] **Video location:** `{status.get('video_path', 'data/shorts/output/')}`

**What would you like to do?**
1. [ARCHIVE] Archive this project and start a new one
2. [EDIT] Make changes to this project
3. [VIEW] Review project details
"""

    else:
        project = status["project"]
        greeting = f"""
{phase["emoji"]} **Current Project: {project['topic'] or 'Untitled'}**

**Phase:** {phase["name"]}
{phase["description"]}

**Status:**
- Script: {'[OK]' if status['files']['script'] else '[--]'}
- Audio: {'[OK]' if status['files']['audio'] else '[--]'}
- Video: {'[OK]' if status['files']['video'] else '[--]'}

**Next Steps:**
"""
        for action in status["next_actions"]:
            greeting += f"- {action}\n"

    return {
        "message": greeting,
        "status": status,
        "phase": phase["id"]
    }
