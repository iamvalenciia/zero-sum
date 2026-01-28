#!/usr/bin/env python3
"""
Zero Sum LDS MCP Server
A Model Context Protocol server for creating LDS short-form video content.

Characters:
- Sister Faith (formerly Analyst): The knowledgeable member who cites prophets, scriptures, testimonies
- Brother Marcus (formerly Skeptic): The curious member learning about doctrine

Key Features (v2.0):
- Unified project management with consistent paths
- Auto-save scripts when generated
- Auto-generate timestamps when rendering
- File management for images (copy/move from any location)

Run with: python server.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    Resource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)
from pydantic import AnyUrl

# Import core modules (use lds_mcp to avoid conflicts with mcp package)
from src.core.elevenlabs import generate_audio_from_script
from lds_mcp.tools.script_generator import create_lds_script
from lds_mcp.tools.content_search import search_lds_content, search_world_news
from lds_mcp.tools.quote_verifier import verify_lds_quote
from lds_mcp.tools.image_manager import ImageManager
from lds_mcp.tools.short_renderer import render_short_video, execute_render
from lds_mcp.tools.project_manager import get_project_manager
from lds_mcp.tools.file_manager import handle_file_operation, FileManager
from lds_mcp.tools.workflow import handle_workflow_operation
from lds_mcp.tools.project_state import (
    get_state_manager,
    get_welcome_message,
    ProjectPhase
)

# Initialize server
server = Server("zero-sum-lds")

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
SHORTS_DIR = DATA_DIR / "shorts"
IMAGES_DIR = DATA_DIR / "images"

# Ensure directories exist
SHORTS_DIR.mkdir(parents=True, exist_ok=True)

# Character configuration for LDS content
# IMPORTANT: Character names must match exactly for ElevenLabs voice mapping
# "Analyst" -> Eve (female), "Skeptic" -> Charles (male)
CHARACTERS = {
    "analyst": {
        "name": "Analyst",
        "role": "The knowledgeable scripture scholar",
        "voice_id": "BZgkqPqms7Kj9ulSkVzn",  # Eve - professional female
        "traits": "Studies scriptures deeply, cites prophets and testimonies. Calm, faithful, precise.",
        "tags": "[softly], [reverently], [with conviction], [warmly], [deep breath], [whispers]"
    },
    "skeptic": {
        "name": "Skeptic",
        "role": "The curious learner",
        "voice_id": "S9GPGBaMND8XWwwzxQXp",  # Charles - young male
        "traits": "Asks sincere questions, represents members learning. Humble, curious.",
        "tags": "[curious], [thoughtfully], [surprised], [realizing], [pondering], [nervous laugh], [sighs]"
    }
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="create_script",
            description="""Create a short-form video script (1-2 minutes) for LDS content.

            The script features two characters:
            - Sister Faith: Knowledgeable member who cites prophets, scriptures, testimonies
            - Brother Marcus: Curious member learning about doctrine

            Returns a JSON script ready for audio generation.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The main topic (e.g., 'The First Vision', 'Faith in Jesus Christ')"
                    },
                    "topic_context": {
                        "type": "string",
                        "description": "Additional context, scriptures, or prophet quotes to include"
                    },
                    "hook_question": {
                        "type": "string",
                        "description": "A compelling question or phrase for the video overlay (3-5 words)"
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Target duration in seconds (60-120 recommended)",
                        "default": 60
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="search_lds_content",
            description="""Search for LDS scriptures, prophet quotes, and church content.

            Sources:
            - Book of Mormon, Doctrine & Covenants, Pearl of Great Price
            - General Conference talks
            - Liahona magazine
            - Church news and official statements

            Returns verified quotes with sources.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'faith', 'Joseph Smith First Vision')"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["scriptures", "conference", "liahona", "all"],
                        "description": "Type of source to search",
                        "default": "all"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_world_news",
            description="""Search for recent world news and find relevant LDS teachings.

            Helps create content that connects current events with gospel principles.
            Returns news summaries with suggested scripture/prophet connections.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "News topic to search (e.g., 'peace', 'hope', 'family')"
                    },
                    "find_gospel_connection": {
                        "type": "boolean",
                        "description": "Whether to suggest related gospel teachings",
                        "default": True
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="verify_quote",
            description="""Verify if a prophet quote or scripture reference is accurate.

            IMPORTANT: Always use this before including quotes in scripts to avoid misinformation.
            Returns verification status and correct citation if found.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "quote": {
                        "type": "string",
                        "description": "The quote text to verify"
                    },
                    "attributed_to": {
                        "type": "string",
                        "description": "Who the quote is attributed to (e.g., 'President Nelson', 'Moroni')"
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional: claimed source (e.g., 'October 2023 Conference')"
                    }
                },
                "required": ["quote", "attributed_to"]
            }
        ),
        Tool(
            name="upload_images",
            description="""Register manually uploaded images for video assembly.

            Upload images to be used in the video. The system will intelligently
            order them based on the script content.

            Images should be placed in: data/shorts/images/
            Returns a list of registered images with suggested placements.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_descriptions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "filename": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        },
                        "description": "List of images with descriptions for intelligent ordering"
                    },
                    "script_id": {
                        "type": "string",
                        "description": "ID of the script to associate images with"
                    }
                },
                "required": ["image_descriptions"]
            }
        ),
        Tool(
            name="generate_audio",
            description="""Generate audio from a script using ElevenLabs voices.

            Uses:
            - Sister Faith: Eve voice (professional, calm)
            - Brother Marcus: Charles voice (young, curious)

            Returns path to generated audio file.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "ID of the script to generate audio for"
                    },
                    "script_json": {
                        "type": "object",
                        "description": "Alternatively, pass the script JSON directly"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="render_short",
            description="""Prepare a short-form video render plan (9:16 vertical format).

            Validates all prerequisites and prepares the render configuration.
            Use execute_render to actually render the video.

            Output: Render plan ready for execution""",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "ID of the script to render"
                    },
                    "hook_text": {
                        "type": "string",
                        "description": "Text to display at top of video (3-5 words)"
                    },
                    "opening_image": {
                        "type": "string",
                        "description": "Path to opening/thumbnail image"
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "Output filename (without extension)",
                        "default": "short_video"
                    }
                },
                "required": ["script_id", "hook_text"]
            }
        ),
        Tool(
            name="execute_render",
            description="""Execute the video render and create the final MP4 file.

            This tool ACTUALLY renders the video using FFmpeg/PyAV.
            It creates the final short-form video (9:16 vertical, 1080x1920).

            Assembles:
            - Opening image/thumbnail with fade
            - Hook text overlay (top of video)
            - Character poses with lip sync
            - Audio narration
            - Word-by-word captions

            Output: Final MP4 file ready for TikTok/Instagram Reels/YouTube Shorts

            NOTE: This may take 1-5 minutes depending on video length.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "ID of the script to render"
                    },
                    "hook_text": {
                        "type": "string",
                        "description": "Text to display at top of video (3-5 words)"
                    },
                    "opening_image": {
                        "type": "string",
                        "description": "Path to opening/thumbnail image (optional)"
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "Output filename (without extension)",
                        "default": "short_video"
                    }
                },
                "required": ["script_id", "hook_text"]
            }
        ),
        Tool(
            name="get_render_log",
            description="""Get the render log file content to see what happened during rendering.

            Use this tool AFTER calling execute_render to see:
            - What step the render is on
            - Any errors that occurred
            - Progress information

            This is essential for debugging render issues.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "tail_lines": {
                        "type": "integer",
                        "description": "Number of lines from end to return (default: 100)",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="check_render_status",
            description="""Check the current status of a background render.

            Returns:
            - phase: current phase (starting, importing, rendering, complete, error)
            - message: human-readable status message
            - progress: percentage complete (0-100)
            - last_updated: when status was last updated
            - logs: last 20 lines from render log

            Use this to monitor render progress in real-time.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_id": {
                        "type": "string",
                        "description": "ID of the script being rendered (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="list_projects",
            description="""List all current short video projects and their status.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_project_status",
            description="""Get detailed status of a specific project.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Project ID to check"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="save_script",
            description="""Save a generated script to the project.

            IMPORTANT: Call this after generating a script JSON to save it to disk.
            This ensures the script is available for audio generation and rendering.

            The script will be:
            1. Saved to data/shorts/scripts/{project_id}.json
            2. Also saved to data/production_plan.json for CLI compatibility
            3. Set as the current active project

            Returns the project_id for subsequent operations.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_json": {
                        "type": "object",
                        "description": "The complete script JSON object to save"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Optional: Override the project ID (defaults to script.id or auto-generated)"
                    }
                },
                "required": ["script_json"]
            }
        ),
        Tool(
            name="manage_files",
            description="""Manage files within the project (copy, move, list, register images).

            Operations:
            - copy: Copy a file from any location to the project
            - move: Move a file within the project
            - register_images: Copy multiple images to a project's images folder
            - list: List directory contents
            - list_project_images: List images registered for a project
            - mkdir: Create a directory
            - delete: Delete a file (requires confirm=true)

            Use this to:
            - Copy images from Downloads or other folders to the project
            - Organize project files
            - List available images""",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["copy", "move", "register_images", "list", "list_project_images", "mkdir", "delete"],
                        "description": "The file operation to perform"
                    },
                    "source": {
                        "type": "string",
                        "description": "Source file path (for copy/move)"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path (for copy/move)"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path (for list/mkdir/delete)"
                    },
                    "image_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of image paths (for register_images)"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID (for register_images/list_project_images)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern for filtering (for list)",
                        "default": "*"
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Overwrite existing files",
                        "default": False
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm deletion (required for delete)",
                        "default": False
                    }
                },
                "required": ["operation"]
            }
        ),
        Tool(
            name="workflow",
            description="""High-level workflow operations for streamlined video creation.

            Operations:
            - create_project: Initialize a new video project with topic
            - finalize_script: Validate and save a generated script JSON
            - produce_video: Check prerequisites and prepare for rendering
            - get_summary: Get actionable project status

            RECOMMENDED FLOW:
            1. workflow(operation="create_project", topic="Your Topic")
            2. [Generate script JSON based on instructions]
            3. workflow(operation="finalize_script", script_json={...})
            4. generate_audio(script_id="...")
            5. render_short(script_id="...", hook_text="...")

            This tool provides clearer guidance at each step.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create_project", "finalize_script", "produce_video", "get_summary"],
                        "description": "The workflow operation to perform"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Video topic (for create_project)"
                    },
                    "topic_context": {
                        "type": "string",
                        "description": "Additional context, quotes, scriptures (for create_project)"
                    },
                    "hook_question": {
                        "type": "string",
                        "description": "Catchy question for video overlay (for create_project)"
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Target video duration (for create_project)",
                        "default": 75
                    },
                    "script_json": {
                        "type": "object",
                        "description": "The generated script JSON (for finalize_script)"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID (optional, uses current project if not specified)"
                    }
                },
                "required": ["operation"]
            }
        ),
        Tool(
            name="get_status",
            description="""Get current project status and phase.

            CALL THIS FIRST when starting a new chat to understand:
            - What project is active (if any)
            - What phase we're in (idea, script, audio, render, complete)
            - What files exist
            - What the next steps are

            This helps avoid confusion and conflicts between projects.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="archive_project",
            description="""Archive the current project to old-videos folder.

            Use this when:
            - A video is complete and you want to start fresh
            - You want to clean up before a new project
            - There are leftover files from a previous project

            Archives all project files (script, audio, timestamps, video) to:
            old-videos/{project_id}_{timestamp}/

            After archiving, the system is ready for a new project.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "delete_source": {
                        "type": "boolean",
                        "description": "Delete source files after archiving (default: true)",
                        "default": True
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID to archive (uses current if not specified)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="cleanup_workspace",
            description="""Clean up all project files to start completely fresh.

            This will:
            1. Archive the current project (if any)
            2. Remove all files from data/shorts/
            3. Reset project state

            Use with caution - this removes all current project data.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "archive_first": {
                        "type": "boolean",
                        "description": "Archive current project before cleanup (default: true)",
                        "default": True
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirm cleanup action (required)",
                        "default": False
                    }
                },
                "required": ["confirm"]
            }
        ),
        Tool(
            name="list_archived",
            description="""List all archived projects in old-videos folder.

            Shows previously completed or archived projects with:
            - Project ID and topic
            - Archive date
            - Files included

            Use this to review past work or restore a project.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    """Handle tool calls."""

    if name == "create_script":
        result = await create_lds_script(
            topic=arguments.get("topic"),
            topic_context=arguments.get("topic_context", ""),
            hook_question=arguments.get("hook_question", ""),
            duration_seconds=arguments.get("duration_seconds", 60),
            characters=CHARACTERS
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "search_lds_content":
        result = await search_lds_content(
            query=arguments.get("query"),
            source_type=arguments.get("source_type", "all"),
            max_results=arguments.get("max_results", 5)
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "search_world_news":
        result = await search_world_news(
            topic=arguments.get("topic"),
            find_gospel_connection=arguments.get("find_gospel_connection", True)
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "verify_quote":
        result = await verify_lds_quote(
            quote=arguments.get("quote"),
            attributed_to=arguments.get("attributed_to"),
            source=arguments.get("source", "")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "upload_images":
        manager = ImageManager(SHORTS_DIR / "images")
        result = await manager.register_images(
            image_descriptions=arguments.get("image_descriptions", []),
            script_id=arguments.get("script_id")
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "generate_audio":
        script_id = arguments.get("script_id")
        script_json = arguments.get("script_json")

        pm = get_project_manager(DATA_DIR.parent)

        # Try to load script from file if script_id provided
        if script_id:
            script_path = SHORTS_DIR / "scripts" / f"{script_id}.json"
            if script_path.exists():
                with open(script_path) as f:
                    script_json = json.load(f)
            # Set as current project
            pm.set_current_project(script_id)

        if not script_json:
            return [TextContent(type="text", text="Error: No script provided or found")]

        # Extract script_id from JSON if not provided
        if not script_id:
            script_content = script_json.get("script", script_json)
            script_id = script_content.get("id")

            # If still no ID, generate one and save the script
            if not script_id:
                script_id = pm.generate_project_id()
                script_json["script"] = script_json.get("script", {})
                script_json["script"]["id"] = script_id
                pm.save_script(script_json, script_id)

        # Get paths from ProjectManager
        paths = pm.get_paths(script_id)

        # Ensure directories exist
        paths.audio_file.parent.mkdir(parents=True, exist_ok=True)

        dialogue = script_json.get("script", {}).get("dialogue", [])

        # If dialogue is empty, try top-level
        if not dialogue and isinstance(script_json.get("dialogue"), list):
            dialogue = script_json.get("dialogue", [])

        if not dialogue:
            return [TextContent(type="text", text="Error: No dialogue found in script")]

        # Generate audio with correct voice mapping
        result = generate_audio_from_script(
            dialogue=dialogue,
            output_file=str(paths.audio_file),
            voice_id_skeptic=CHARACTERS["skeptic"]["voice_id"],
            voice_id_analyst=CHARACTERS["analyst"]["voice_id"]
        )

        # Create legacy copy for CLI compatibility
        try:
            import shutil
            paths.legacy_audio.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(paths.audio_file, paths.legacy_audio)
        except Exception as e:
            print(f"Warning: Could not create legacy audio copy: {e}")

        response = {
            "status": "success",
            "project_id": script_id,
            "audio_file": str(paths.audio_file),
            "legacy_copy": str(paths.legacy_audio),
            "message": result,
            "next_steps": [
                f"Render video: use render_short with script_id='{script_id}'",
                "Timestamps will be auto-generated during render"
            ]
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    elif name == "render_short":
        script_id = arguments.get("script_id")

        # Set as current project
        pm = get_project_manager(DATA_DIR.parent)
        if script_id:
            pm.set_current_project(script_id)

        result = await render_short_video(
            script_id=script_id,
            hook_text=arguments.get("hook_text"),
            opening_image=arguments.get("opening_image"),
            output_filename=arguments.get("output_filename", script_id or "short_video"),
            shorts_dir=SHORTS_DIR,
            auto_generate_timestamps=True  # Auto-generate if missing
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "execute_render":
        print(f"[MCP_SERVER] execute_render called", file=sys.stderr, flush=True)
        print(f"[MCP_SERVER] arguments: {arguments}", file=sys.stderr, flush=True)

        script_id = arguments.get("script_id")
        hook_text = arguments.get("hook_text", "")
        opening_image = arguments.get("opening_image", "")
        output_filename = arguments.get("output_filename", script_id or "short_video")

        print(f"[MCP_SERVER] script_id={script_id}, hook_text={hook_text}", file=sys.stderr, flush=True)

        # Set as current project
        pm = get_project_manager(DATA_DIR.parent)
        if script_id:
            pm.set_current_project(script_id)

        # Validate prerequisites BEFORE starting render
        script_path = SHORTS_DIR / "scripts" / f"{script_id}.json"
        audio_path = SHORTS_DIR / "audio" / f"{script_id}.mp3"

        if not script_path.exists():
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "message": f"Script not found: {script_path}",
                "action_required": "Create a script first using create_script or save_script"
            }, indent=2))]

        if not audio_path.exists():
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "message": f"Audio not found: {audio_path}",
                "action_required": "Generate audio first using generate_audio"
            }, indent=2))]

        # Initialize status file
        status_file = SHORTS_DIR / "render_status.json"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({
                "phase": "starting",
                "message": "Launching render process...",
                "progress": 0,
                "script_id": script_id,
                "started_at": datetime.now().isoformat()
            }, f, indent=2)

        # Launch render worker as separate process
        # This ensures render continues even if MCP client disconnects
        import subprocess
        worker_script = Path(__file__).parent / "tools" / "render_worker.py"

        # Create log file for worker output
        worker_log = DATA_DIR / "render_worker.log"

        try:
            # Build command
            cmd = [
                sys.executable,  # Use same Python interpreter
                str(worker_script),
                script_id,
                hook_text,
                opening_image or "",
                output_filename
            ]

            print(f"[MCP_SERVER] Launching worker: {' '.join(cmd)}", file=sys.stderr, flush=True)

            # Launch detached process (continues after MCP disconnects)
            # On Windows, use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
            if sys.platform == "win32":
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                with open(worker_log, "w") as log_f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                        close_fds=True
                    )
            else:
                # Unix: use nohup-like approach
                with open(worker_log, "w") as log_f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                        close_fds=True
                    )

            result = {
                "status": "started",
                "message": "Render started in background! Use check_render_status to monitor progress.",
                "script_id": script_id,
                "pid": process.pid,
                "status_file": str(status_file),
                "worker_log": str(worker_log),
                "instructions": [
                    "1. Render is now running in the background",
                    "2. Use check_render_status to see progress and logs",
                    "3. You can close this chat - render will continue",
                    "4. Final video will be at: data/shorts/output/" + output_filename + ".mp4"
                ]
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            print(f"[MCP_SERVER] Failed to launch worker: {e}", file=sys.stderr, flush=True)
            error_result = {
                "status": "error",
                "message": f"Failed to launch render worker: {str(e)}",
                "traceback": error_tb
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    elif name == "get_render_log":
        # Read the render log file
        log_file = DATA_DIR / "render_log.txt"
        tail_lines = arguments.get("tail_lines", 100)

        try:
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Get last N lines
                if len(lines) > tail_lines:
                    lines = lines[-tail_lines:]

                log_content = "".join(lines)
                result = {
                    "status": "success",
                    "log_file": str(log_file),
                    "total_lines": len(lines),
                    "content": log_content
                }
            else:
                result = {
                    "status": "no_log",
                    "message": f"Log file not found: {log_file}",
                    "hint": "Run execute_render first to generate logs"
                }
        except Exception as e:
            result = {
                "status": "error",
                "message": str(e)
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "check_render_status":
        # Check status of background render
        status_file = SHORTS_DIR / "render_status.json"
        log_file = DATA_DIR / "render_log.txt"

        result = {
            "status": "unknown",
            "phase": "unknown",
            "message": "No render status available"
        }

        # Read status file if exists
        try:
            if status_file.exists():
                with open(status_file, "r", encoding="utf-8") as f:
                    result = json.load(f)
                result["status"] = "found"
        except Exception as e:
            result["status_error"] = str(e)

        # Always include recent logs
        try:
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                result["logs"] = "".join(lines[-30:])  # Last 30 lines
                result["log_lines_total"] = len(lines)
        except Exception as e:
            result["log_error"] = str(e)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "list_projects":
        pm = get_project_manager(DATA_DIR.parent)
        projects = pm.list_projects()
        current = pm.get_current_project()

        result = {
            "current_project": current,
            "projects": projects
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_project_status":
        project_id = arguments.get("project_id")
        pm = get_project_manager(DATA_DIR.parent)
        try:
            status = pm.get_project_status(project_id)
        except:
            status = {
                "project_id": project_id,
                "script": (SHORTS_DIR / "scripts" / f"{project_id}.json").exists(),
                "audio": (SHORTS_DIR / "audio" / f"{project_id}.mp3").exists(),
                "timestamps": (SHORTS_DIR / "audio" / f"{project_id}_timestamps.json").exists(),
                "images": list((SHORTS_DIR / "images").glob(f"{project_id}_*")) if (SHORTS_DIR / "images").exists() else [],
                "video": (SHORTS_DIR / "output" / f"{project_id}.mp4").exists()
            }
        return [TextContent(type="text", text=json.dumps(status, indent=2))]

    elif name == "save_script":
        script_json = arguments.get("script_json")
        project_id = arguments.get("project_id")

        if not script_json:
            return [TextContent(type="text", text="Error: script_json is required")]

        pm = get_project_manager(DATA_DIR.parent)

        try:
            saved_id = pm.save_script(script_json, project_id)
            paths = pm.get_paths(saved_id)

            result = {
                "status": "success",
                "project_id": saved_id,
                "saved_to": str(paths.script_file),
                "legacy_copy": str(paths.legacy_production_plan),
                "next_steps": [
                    f"Generate audio: use generate_audio with script_id='{saved_id}'",
                    f"Or render directly: use render_short with script_id='{saved_id}'"
                ]
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error saving script: {str(e)}")]

    elif name == "manage_files":
        operation = arguments.get("operation")

        if not operation:
            return [TextContent(type="text", text="Error: operation is required")]

        result = await handle_file_operation(
            operation=operation,
            arguments=arguments,
            base_dir=DATA_DIR.parent
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "workflow":
        operation = arguments.get("operation")

        if not operation:
            return [TextContent(type="text", text="Error: operation is required")]

        result = await handle_workflow_operation(
            operation=operation,
            arguments=arguments,
            base_dir=DATA_DIR.parent
        )

        # Update project state when workflow creates/updates project
        if operation == "create_project" and result.get("status") == "project_created":
            sm = get_state_manager(DATA_DIR.parent)
            sm.start_new_project(
                project_id=result.get("project_id"),
                topic=result.get("topic", ""),
                hook_text=result.get("parameters", {}).get("hook_question", "")
            )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_status":
        # Get comprehensive status report
        welcome = get_welcome_message()
        sm = get_state_manager(DATA_DIR.parent)
        status_report = sm.get_status_report()

        result = {
            "welcome_message": welcome["message"],
            "phase": welcome["phase"],
            "status": status_report
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "archive_project":
        sm = get_state_manager(DATA_DIR.parent)
        project_id = arguments.get("project_id")
        delete_source = arguments.get("delete_source", True)

        # If specific project_id, update state first
        if project_id:
            sm._state.project_id = project_id
            sm.refresh_state()

        result = sm.archive_current_project(delete_after=delete_source)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "cleanup_workspace":
        confirm = arguments.get("confirm", False)
        archive_first = arguments.get("archive_first", True)

        if not confirm:
            return [TextContent(type="text", text=json.dumps({
                "status": "confirmation_required",
                "message": "This will remove all project files. Set confirm=true to proceed.",
                "warning": "All files in data/shorts/ will be deleted (archived first if archive_first=true)"
            }, indent=2))]

        sm = get_state_manager(DATA_DIR.parent)
        result = sm.cleanup_all(archive_first=archive_first)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "list_archived":
        sm = get_state_manager(DATA_DIR.parent)
        archived = sm.list_archived_projects()

        result = {
            "archived_projects": archived,
            "total": len(archived),
            "archive_location": str(sm.archive_dir)
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts for common tasks."""
    return [
        Prompt(
            name="welcome",
            description="Start here! Check project status and get guidance on what to do next.",
            arguments=[]
        ),
        Prompt(
            name="new_video",
            description="Start creating a new video from scratch",
            arguments=[
                {"name": "topic", "description": "Video topic", "required": True}
            ]
        ),
        Prompt(
            name="daily_inspiration",
            description="Create a daily inspirational short connecting world events with gospel principles",
            arguments=[
                {"name": "news_topic", "description": "Current event or theme", "required": False}
            ]
        ),
        Prompt(
            name="scripture_explanation",
            description="Create a short explaining a scripture or doctrine",
            arguments=[
                {"name": "scripture", "description": "Scripture reference", "required": True}
            ]
        ),
        Prompt(
            name="prophet_teaching",
            description="Create a short based on a prophet's teaching",
            arguments=[
                {"name": "prophet", "description": "Prophet name", "required": True},
                {"name": "topic", "description": "Teaching topic", "required": True}
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    """Get a specific prompt template."""

    if name == "welcome":
        # Get current status
        welcome = get_welcome_message()
        sm = get_state_manager(DATA_DIR.parent)
        status = sm.get_status_report()

        # Build contextual welcome message
        phase = status["current_phase"]

        if phase["id"] == "idle":
            prompt_text = f"""{welcome['message']}

I've checked your project status. You have no active project.

**Options:**
1. Tell me a topic and I'll help you create a new video
2. Say "list archived" to see your previous projects
3. Ask me anything about LDS video creation

What would you like to do?"""

        elif phase["id"] == "complete":
            project = status["project"]
            prompt_text = f"""{welcome['message']}

Your video for **"{project['topic']}"** is complete!

**Options:**
1. Say "archive" to save this project and start fresh
2. Say "show video" to see the output location
3. Tell me a new topic to start another video

What would you like to do?"""

        else:
            project = status["project"]
            files = status["files"]

            prompt_text = f"""{welcome['message']}

**Current project:** {project.get('topic', 'Untitled')} ({project.get('id', 'unknown')})

**Progress:**
- Script: {'Done' if files['script'] else 'Pending'}
- Audio: {'Done' if files['audio'] else 'Pending'}
- Video: {'Done' if files['video'] else 'Pending'}

**Next steps:**
"""
            for action in status["next_actions"]:
                prompt_text += f"- {action}\n"

            prompt_text += "\nWould you like me to continue with the next step?"

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )

    elif name == "new_video":
        topic = arguments.get("topic", "")

        # Check for existing project
        sm = get_state_manager(DATA_DIR.parent)
        status = sm.get_status_report()

        if status["current_phase"]["id"] not in ["idle", "archived"]:
            existing_topic = status["project"].get("topic", "Unknown")
            prompt_text = f"""You want to create a new video about: **{topic}**

However, there's an existing project for "{existing_topic}".

**Options:**
1. Archive the current project and start fresh with "{topic}"
2. Continue working on "{existing_topic}"
3. Abandon current project (not recommended)

What would you like to do?"""
        else:
            prompt_text = f"""Let's create a new video about: **{topic}**

I'll guide you through each step:

1. **IDEA** - Research scriptures and prophet quotes
2. **SCRIPT** - Create the dialogue between Analyst and Skeptic
3. **AUDIO** - Generate voices with ElevenLabs
4. **RENDER** - Create the final video with lip-sync

First, let me search for relevant content about "{topic}"...

Use these tools:
- search_lds_content to find scriptures
- workflow(operation="create_project", topic="{topic}") to initialize"""

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=prompt_text
                    )
                )
            ]
        )

    elif name == "daily_inspiration":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Create an inspirational LDS short video about: {arguments.get('news_topic', 'finding peace in troubled times')}

Steps:
1. First, use search_world_news to find relevant current events
2. Use search_lds_content to find related scriptures and prophet quotes
3. Use verify_quote to ensure all quotes are accurate
4. Use create_script to generate the dialogue
5. Show me the script for approval before generating audio"""
                    )
                )
            ]
        )

    elif name == "scripture_explanation":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Create an LDS short explaining: {arguments.get('scripture')}

Steps:
1. Use search_lds_content to get context about this scripture
2. Use create_script with this context
3. Show me the script for approval"""
                    )
                )
            ]
        )

    elif name == "prophet_teaching":
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Create an LDS short about {arguments.get('prophet')}'s teaching on {arguments.get('topic')}

Steps:
1. Use search_lds_content to find quotes from {arguments.get('prophet')}
2. Use verify_quote on each quote found
3. Use create_script with verified quotes
4. Show me the script for approval"""
                    )
                )
            ]
        )

    return GetPromptResult(messages=[])


async def main():
    """Run the MCP server."""
    print("Starting Zero Sum LDS MCP Server...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
