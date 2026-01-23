#!/usr/bin/env python3
"""
Zero Sum LDS MCP Server
A Model Context Protocol server for creating LDS short-form video content.

Characters:
- Sister Faith (formerly Analyst): The knowledgeable member who cites prophets, scriptures, testimonies
- Brother Marcus (formerly Skeptic): The curious member learning about doctrine

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

# Import core modules
from src.core.elevenlabs import generate_audio_from_script
from mcp.tools.script_generator import create_lds_script
from mcp.tools.content_search import search_lds_content, search_world_news
from mcp.tools.quote_verifier import verify_lds_quote
from mcp.tools.image_manager import ImageManager
from mcp.tools.short_renderer import render_short_video

# Initialize server
server = Server("zero-sum-lds")

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
SHORTS_DIR = DATA_DIR / "shorts"
IMAGES_DIR = DATA_DIR / "images"

# Ensure directories exist
SHORTS_DIR.mkdir(parents=True, exist_ok=True)

# Character configuration for LDS content
CHARACTERS = {
    "sister_faith": {
        "name": "Sister Faith",
        "role": "The knowledgeable member",
        "voice_id": "BZgkqPqms7Kj9ulSkVzn",  # Eve - professional female
        "traits": "Cites prophets, scriptures, and testimonies. Calm, faithful, precise.",
        "tags": "[softly], [reverently], [with conviction], [warmly]"
    },
    "brother_marcus": {
        "name": "Brother Marcus",
        "role": "The curious learner",
        "voice_id": "S9GPGBaMND8XWwwzxQXp",  # Charles - young male
        "traits": "Asks sincere questions, represents members learning. Humble, curious.",
        "tags": "[curious], [thoughtfully], [surprised], [realizing]"
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
            description="""Render the final short-form video (9:16 vertical format).

            Assembles:
            - Opening image/thumbnail
            - Hook text overlay (top of video)
            - Character animations with lip sync
            - Audio narration
            - Captions

            Output: MP4 file ready for TikTok/Reels/Shorts""",
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

        if script_id:
            script_path = SHORTS_DIR / "scripts" / f"{script_id}.json"
            if script_path.exists():
                with open(script_path) as f:
                    script_json = json.load(f)

        if not script_json:
            return [TextContent(type="text", text="Error: No script provided or found")]

        # Generate audio
        output_path = SHORTS_DIR / "audio" / f"{script_id or 'dialogue'}.mp3"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        dialogue = script_json.get("script", {}).get("dialogue", [])

        # Map character names to voice IDs
        result = generate_audio_from_script(
            dialogue=dialogue,
            output_file=str(output_path),
            voice_id_skeptic=CHARACTERS["brother_marcus"]["voice_id"],
            voice_id_analyst=CHARACTERS["sister_faith"]["voice_id"]
        )

        return [TextContent(type="text", text=f"Audio generated: {output_path}\n{result}")]

    elif name == "render_short":
        result = await render_short_video(
            script_id=arguments.get("script_id"),
            hook_text=arguments.get("hook_text"),
            opening_image=arguments.get("opening_image"),
            output_filename=arguments.get("output_filename", "short_video"),
            shorts_dir=SHORTS_DIR
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "list_projects":
        projects = []
        scripts_dir = SHORTS_DIR / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.json"):
                project_id = script_file.stem
                projects.append({
                    "id": project_id,
                    "script": script_file.exists(),
                    "audio": (SHORTS_DIR / "audio" / f"{project_id}.mp3").exists(),
                    "video": (SHORTS_DIR / "output" / f"{project_id}.mp4").exists()
                })
        return [TextContent(type="text", text=json.dumps({"projects": projects}, indent=2))]

    elif name == "get_project_status":
        project_id = arguments.get("project_id")
        status = {
            "project_id": project_id,
            "script": (SHORTS_DIR / "scripts" / f"{project_id}.json").exists(),
            "audio": (SHORTS_DIR / "audio" / f"{project_id}.mp3").exists(),
            "timestamps": (SHORTS_DIR / "audio" / f"{project_id}_timestamps.json").exists(),
            "images": list((SHORTS_DIR / "images").glob(f"{project_id}_*")) if (SHORTS_DIR / "images").exists() else [],
            "video": (SHORTS_DIR / "output" / f"{project_id}.mp4").exists()
        }
        return [TextContent(type="text", text=json.dumps(status, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts for common tasks."""
    return [
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

    if name == "daily_inspiration":
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
