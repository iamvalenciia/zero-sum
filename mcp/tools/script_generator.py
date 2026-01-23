"""
Script Generator for LDS Short-Form Content
Creates dialogue scripts featuring Sister Faith and Brother Marcus.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path


# Prompt template for LDS short-form content
LDS_SCRIPT_PROMPT = """
{
  "input_data": {
    "topic": "{topic}",
    "topic_context": "{topic_context}",
    "hook_question": "{hook_question}"
  },
  "instructions": {
    "Task": "Act as the Executive Producer for LDS educational short-form content. Create a viral 9:16 vertical video script optimized for TikTok/Reels/Shorts.",
    "Goal": "Produce a script with a runtime of {duration_seconds} seconds (approximately {word_count} words). The content must be faith-promoting, doctrinally accurate, and emotionally engaging.",
    "Audience": "Members of The Church of Jesus Christ of Latter-day Saints (Mormons) seeking spiritual growth, understanding, and community.",
    "Persona": {
      "Character_A": {
        "Name": "Sister Faith",
        "Role": "The Knowledgeable Member",
        "Traits": "Cites prophets, scriptures, and testimonies with precision. Warm, faithful, reverent. Uses tags: [softly], [reverently], [with conviction], [warmly], [smiling]."
      },
      "Character_B": {
        "Name": "Brother Marcus",
        "Role": "The Curious Learner",
        "Traits": "Represents members seeking to understand doctrine better. Sincere questions, humble curiosity. Uses tags: [curious], [thoughtfully], [surprised], [realizing], [pondering]."
      },
      "Viewer_Experience": "The viewer feels understood. Their questions are validated, and they receive clear, faith-affirming answers."
    },
    "Content_Guidelines": {
      "Tone": "Always faith-promoting and positive about the Church",
      "Sources": "Only cite verified scriptures, prophet quotes, and official Church sources",
      "Accuracy": "Never contradict official Church doctrine",
      "Goal": "Build a faithful community, help members understand doctrine"
    },
    "Context": {
      "Structure": "Start 'In Media Res' (mid-conversation). Brother Marcus asks a sincere question. Sister Faith provides a clear, scriptural answer.",
      "Pacing": "Quick exchanges. Each response should be concise but impactful.",
      "Ending": "End with a powerful testimony, scripture, or reflection that invites the viewer to ponder."
    },
    "Format": {
      "Text_Normalization": "Strictly NO DIGITS. Write '1830' as 'eighteen thirty', 'D&C 121' as 'Doctrine and Covenants one twenty-one'.",
      "Audio_Engineering": "ElevenLabs V3 optimization. Use emotion tags for natural delivery.",
      "Visual_Strategy": {
        "Opening": "Start with a compelling image while first line plays",
        "Hook_Text": "Display '{hook_question}' at the top of the video throughout",
        "Characters": "Alternate between Sister Faith and Brother Marcus poses"
      },
      "Cinematography_Rules": {
        "Requirement": "Every dialogue object MUST include a 'character_poses' array.",
        "Poses_Available": [
          { "id": "sister_faith_close", "character": "Sister Faith", "description": "Close-up. Sharing testimony, profound truths." },
          { "id": "sister_faith_front", "character": "Sister Faith", "description": "Medium shot. Teaching, explaining doctrine." },
          { "id": "sister_faith_pov", "character": "Sister Faith", "description": "POV shot. Responding to questions." },
          { "id": "brother_marcus_close", "character": "Brother Marcus", "description": "Close-up. Realization, emotion, pondering." },
          { "id": "brother_marcus_front", "character": "Brother Marcus", "description": "Medium shot. Asking questions, listening." },
          { "id": "brother_marcus_side", "character": "Brother Marcus", "description": "Side profile. Thinking, reflecting." }
        ]
      },
      "Output_Structure": "Output ONLY valid JSON following the template below."
    },
    "Output_JSON_Template": {
      "script": {
        "id": "unique_id",
        "topic": "topic_name",
        "hook_text": "hook_question for overlay",
        "duration_target_seconds": 60,
        "dialogue": [
          {
            "character": "Brother Marcus",
            "text": "[curious] ...but I have always wondered, why is this so important?",
            "character_poses": [
              { "pose_id": "brother_marcus_front", "start_word_index": 0, "end_word_index": 10 }
            ],
            "visual_assets": null
          },
          {
            "character": "Sister Faith",
            "text": "[warmly] That is such a great question. Let me share what President Nelson taught...",
            "character_poses": [
              { "pose_id": "sister_faith_front", "start_word_index": 0, "end_word_index": 15 }
            ],
            "visual_assets": null
          }
        ]
      }
    }
  }
}
"""


async def create_lds_script(
    topic: str,
    topic_context: str = "",
    hook_question: str = "",
    duration_seconds: int = 60,
    characters: dict = None
) -> dict:
    """
    Create an LDS short-form video script.

    This function prepares the prompt and structure for script generation.
    The actual AI generation happens in Claude Desktop using this prepared context.

    Args:
        topic: Main topic for the video
        topic_context: Additional context (scriptures, quotes, etc.)
        hook_question: Compelling question for video overlay
        duration_seconds: Target duration (60-120 seconds)
        characters: Character configuration

    Returns:
        dict: Script template ready for generation or approval
    """

    # Calculate approximate word count (150 words per minute for spoken content)
    word_count = int((duration_seconds / 60) * 150)

    # Generate unique script ID
    script_id = f"lds_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Prepare the prompt
    prompt = LDS_SCRIPT_PROMPT.format(
        topic=topic,
        topic_context=topic_context or "No additional context provided. Please research and include relevant scriptures and prophet quotes.",
        hook_question=hook_question or f"What about {topic}?",
        duration_seconds=duration_seconds,
        word_count=word_count
    )

    # Return structure for Claude to complete
    result = {
        "status": "ready_for_generation",
        "script_id": script_id,
        "parameters": {
            "topic": topic,
            "topic_context": topic_context,
            "hook_question": hook_question or f"What about {topic}?",
            "duration_seconds": duration_seconds,
            "word_count_target": word_count
        },
        "characters": {
            "sister_faith": {
                "name": "Sister Faith",
                "role": "The knowledgeable member who cites prophets, scriptures, testimonies",
                "poses": ["sister_faith_close", "sister_faith_front", "sister_faith_pov"]
            },
            "brother_marcus": {
                "name": "Brother Marcus",
                "role": "The curious learner asking sincere questions",
                "poses": ["brother_marcus_close", "brother_marcus_front", "brother_marcus_side"]
            }
        },
        "generation_prompt": prompt,
        "instructions": """
To generate the script, Claude should:
1. Use the topic and context provided
2. Create a natural dialogue between Sister Faith and Brother Marcus
3. Include accurate scripture references and prophet quotes
4. Format the output as valid JSON matching the template
5. Include emotion tags for ElevenLabs: [warmly], [reverently], [curious], etc.
6. Assign appropriate poses to each dialogue line

After generation, save the script to: data/shorts/scripts/{script_id}.json
""",
        "pose_mapping": {
            "sister_faith_close": "analyst_close",
            "sister_faith_front": "analyst_front",
            "sister_faith_pov": "analyst_pov",
            "brother_marcus_close": "skeptic_close",
            "brother_marcus_front": "skeptic_front",
            "brother_marcus_side": "skeptic_side"
        }
    }

    return result


def save_script(script_data: dict, scripts_dir: Path) -> str:
    """Save a generated script to disk."""
    scripts_dir.mkdir(parents=True, exist_ok=True)

    script_id = script_data.get("script", {}).get("id", f"script_{uuid.uuid4().hex[:8]}")
    script_path = scripts_dir / f"{script_id}.json"

    with open(script_path, "w") as f:
        json.dump(script_data, f, indent=2)

    return str(script_path)


def load_script(script_id: str, scripts_dir: Path) -> dict:
    """Load a script from disk."""
    script_path = scripts_dir / f"{script_id}.json"

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_id}")

    with open(script_path) as f:
        return json.load(f)
