"""
Workflow Orchestrator for LDS Video Creation Pipeline.

This module provides high-level workflows that combine multiple tools
into streamlined operations, reducing manual intervention.

Key Workflows:
1. create_video_project - Initialize a new project with topic
2. finalize_script - Validate and save a generated script
3. produce_video - Generate audio and render video in one step
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from lds_mcp.tools.project_manager import get_project_manager


class WorkflowOrchestrator:
    """
    Orchestrates the video creation pipeline with intelligent automation.

    This class reduces manual steps by:
    - Auto-validating scripts before saving
    - Providing clear, actionable next steps
    - Tracking project state across operations
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.pm = get_project_manager(base_dir)
        self.base_dir = self.pm.base_dir

    async def create_video_project(
        self,
        topic: str,
        topic_context: str = "",
        hook_question: str = "",
        duration_seconds: int = 75
    ) -> Dict[str, Any]:
        """
        Initialize a new video project with a topic.

        This is the first step in the pipeline. It:
        1. Creates a unique project ID
        2. Prepares the script generation context
        3. Returns clear instructions for the next step

        Args:
            topic: Main topic for the video
            topic_context: Additional context (quotes, scriptures, etc.)
            hook_question: Catchy question for the video overlay
            duration_seconds: Target video duration

        Returns:
            Project initialization data with next steps
        """
        project_id = self.pm.generate_project_id()
        self.pm.set_current_project(project_id)

        word_count = int((duration_seconds / 60) * 150)

        return {
            "status": "project_created",
            "project_id": project_id,
            "topic": topic,
            "parameters": {
                "topic": topic,
                "topic_context": topic_context or "No additional context",
                "hook_question": hook_question or f"What about {topic}?",
                "duration_seconds": duration_seconds,
                "word_count_target": word_count
            },
            "characters": {
                "Analyst": {
                    "role": "Scripture scholar (female voice - Eve)",
                    "voice_id": "BZgkqPqms7Kj9ulSkVzn",
                    "emotion_tags": ["[softly]", "[reverently]", "[with conviction]", "[warmly]"]
                },
                "Skeptic": {
                    "role": "Curious learner (male voice - Charles)",
                    "voice_id": "S9GPGBaMND8XWwwzxQXp",
                    "emotion_tags": ["[curious]", "[thoughtfully]", "[realizing]", "[pondering]"]
                }
            },
            "next_step": {
                "action": "Generate the script JSON",
                "instructions": f"""
Generate a dialogue script as valid JSON with this structure:

{{
  "script": {{
    "id": "{project_id}",
    "topic": "{topic}",
    "hook_text": "{hook_question or topic}",
    "dialogue": [
      {{"character": "Skeptic", "text": "[curious] Your question here..."}},
      {{"character": "Analyst", "text": "[warmly] Your response here..."}}
    ]
  }}
}}

IMPORTANT:
- Use EXACTLY "Analyst" or "Skeptic" as character names
- Include emotion tags like [curious], [warmly], [reverently]
- Target ~{word_count} words total

After generating, call: finalize_script(script_json)
""",
                "tool_to_call": "finalize_script"
            }
        }

    async def finalize_script(
        self,
        script_json: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate and save a generated script.

        This step:
        1. Validates the JSON structure
        2. Checks character names are correct
        3. Saves to both new and legacy locations
        4. Returns clear next steps

        Args:
            script_json: The complete script JSON
            project_id: Optional project ID (uses current if not specified)

        Returns:
            Save result with next steps
        """
        try:
            # Use current project if not specified
            pid = project_id or self.pm.get_current_project()
            if not pid:
                pid = self.pm.generate_project_id()

            # Validate and save
            saved_id = self.pm.save_script(script_json, pid)
            paths = self.pm.get_paths(saved_id)

            # Count dialogue lines
            dialogue = script_json.get("script", script_json).get("dialogue", [])
            analyst_lines = sum(1 for d in dialogue if d.get("character") in ["Analyst", "Sister Faith"])
            skeptic_lines = sum(1 for d in dialogue if d.get("character") in ["Skeptic", "Brother Marcus"])

            return {
                "status": "script_saved",
                "project_id": saved_id,
                "saved_to": str(paths.script_file),
                "validation": {
                    "dialogue_lines": len(dialogue),
                    "analyst_lines": analyst_lines,
                    "skeptic_lines": skeptic_lines,
                    "has_valid_characters": True
                },
                "next_step": {
                    "action": "Generate audio",
                    "instructions": f"Call generate_audio with script_id='{saved_id}'",
                    "tool_to_call": "generate_audio",
                    "parameters": {"script_id": saved_id}
                }
            }

        except ValueError as e:
            # Validation error
            return {
                "status": "validation_error",
                "error": str(e),
                "fix_instructions": """
Please fix the script JSON:

1. Ensure character names are exactly "Analyst" or "Skeptic"
2. Each dialogue line must have "character" and "text" fields
3. The dialogue array must not be empty

Example valid dialogue:
{
  "script": {
    "id": "my_script",
    "dialogue": [
      {"character": "Skeptic", "text": "[curious] Question here..."},
      {"character": "Analyst", "text": "[warmly] Response here..."}
    ]
  }
}
"""
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def produce_video(
        self,
        project_id: Optional[str] = None,
        hook_text: Optional[str] = None,
        skip_audio: bool = False
    ) -> Dict[str, Any]:
        """
        Produce the final video (audio + render).

        This step:
        1. Checks if audio exists, generates if needed
        2. Auto-generates timestamps if missing
        3. Renders the final video

        Args:
            project_id: Project to render (uses current if not specified)
            hook_text: Text overlay (uses script hook_text if not specified)
            skip_audio: If True, assumes audio already exists

        Returns:
            Production result with video path
        """
        pid = project_id or self.pm.get_current_project()
        if not pid:
            return {
                "status": "error",
                "error": "No project specified and no current project set"
            }

        paths = self.pm.get_paths(pid)
        status = self.pm.get_project_status(pid)

        # Check prerequisites
        if not status["exists"]["script"]:
            return {
                "status": "error",
                "error": "Script not found. Run finalize_script first.",
                "project_id": pid
            }

        # Load script to get hook_text if not provided
        if not hook_text and paths.script_file.exists():
            with open(paths.script_file) as f:
                script = json.load(f)
                hook_text = script.get("script", script).get("hook_text", "")

        steps_completed = []
        steps_remaining = []

        # Check audio
        if not status["exists"]["audio"] and not skip_audio:
            steps_remaining.append({
                "step": "generate_audio",
                "reason": "Audio file not found",
                "action": f"Call generate_audio with script_id='{pid}'"
            })
        else:
            steps_completed.append("audio")

        # Check timestamps (will be auto-generated during render)
        if not status["exists"]["timestamps"]:
            steps_completed.append("timestamps (will be auto-generated)")

        # Check if ready to render
        if steps_remaining:
            return {
                "status": "prerequisites_missing",
                "project_id": pid,
                "steps_completed": steps_completed,
                "steps_remaining": steps_remaining,
                "next_action": steps_remaining[0]["action"]
            }

        # All prerequisites met, provide render instructions
        return {
            "status": "ready_to_render",
            "project_id": pid,
            "hook_text": hook_text,
            "render_command": {
                "tool": "render_short",
                "parameters": {
                    "script_id": pid,
                    "hook_text": hook_text,
                    "output_filename": pid
                }
            },
            "output_path": str(paths.output_file),
            "note": "Timestamps will be auto-generated if missing during render"
        }

    def get_project_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a comprehensive summary of a project's status.

        Returns actionable information about what's done and what's next.
        """
        pid = project_id or self.pm.get_current_project()
        if not pid:
            return {
                "status": "no_project",
                "message": "No current project. Start with create_video_project."
            }

        status = self.pm.get_project_status(pid)
        paths = self.pm.get_paths(pid)

        # Determine next action
        if not status["exists"]["script"]:
            next_action = "Create and save script with finalize_script"
        elif not status["exists"]["audio"]:
            next_action = f"Generate audio with generate_audio(script_id='{pid}')"
        elif not status["exists"]["video"]:
            next_action = f"Render video with render_short(script_id='{pid}')"
        else:
            next_action = "Project complete! Video is ready."

        return {
            "project_id": pid,
            "status": status["exists"],
            "paths": status["paths"],
            "images_count": len(status.get("images", [])),
            "ready_for_render": status["ready_for_render"],
            "next_action": next_action
        }


async def handle_workflow_operation(
    operation: str,
    arguments: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Handle workflow operations from MCP tool calls.

    Operations:
    - create_project: Initialize a new video project
    - finalize_script: Validate and save a generated script
    - produce_video: Generate audio and render
    - get_summary: Get project status summary
    """
    orchestrator = WorkflowOrchestrator(base_dir)

    if operation == "create_project":
        return await orchestrator.create_video_project(
            topic=arguments.get("topic", ""),
            topic_context=arguments.get("topic_context", ""),
            hook_question=arguments.get("hook_question", ""),
            duration_seconds=arguments.get("duration_seconds", 75)
        )

    elif operation == "finalize_script":
        return await orchestrator.finalize_script(
            script_json=arguments.get("script_json", {}),
            project_id=arguments.get("project_id")
        )

    elif operation == "produce_video":
        return await orchestrator.produce_video(
            project_id=arguments.get("project_id"),
            hook_text=arguments.get("hook_text"),
            skip_audio=arguments.get("skip_audio", False)
        )

    elif operation == "get_summary":
        return orchestrator.get_project_summary(
            project_id=arguments.get("project_id")
        )

    else:
        return {
            "status": "error",
            "message": f"Unknown operation: {operation}",
            "available_operations": ["create_project", "finalize_script", "produce_video", "get_summary"]
        }
