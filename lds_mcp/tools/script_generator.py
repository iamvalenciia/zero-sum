"""
Script Generator for LDS Short-Form Content
Creates dialogue scripts featuring Analyst (knowledgeable) and Skeptic (curious learner).
Character names match ElevenLabs voice mapping for correct audio generation.

STANDARD POSE IDS (from ImageLoader):
- analyst_close  : Close-up for testimony, whispers
- analyst_front  : Medium shot for teaching (DEFAULT)
- analyst_pov    : POV from Skeptic's perspective
- skeptic_close  : Close-up for realization, emotion
- skeptic_front  : Medium shot for questions (DEFAULT)
- skeptic_side   : Side profile for reflection
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Import standard pose definitions from ImageLoader
try:
    from lds_mcp.tools.image_loader import STANDARD_POSES, STANDARD_CHARACTERS
except ImportError:
    # Fallback if ImageLoader not available
    STANDARD_POSES = {
        "analyst_close": {"character": "Analyst", "type": "close"},
        "analyst_front": {"character": "Analyst", "type": "front"},
        "analyst_pov": {"character": "Analyst", "type": "pov"},
        "skeptic_close": {"character": "Skeptic", "type": "close"},
        "skeptic_front": {"character": "Skeptic", "type": "front"},
        "skeptic_side": {"character": "Skeptic", "type": "side"},
    }
    STANDARD_CHARACTERS = {
        "analyst": type('obj', (object,), {"default_pose": "analyst_front"})(),
        "skeptic": type('obj', (object,), {"default_pose": "skeptic_front"})(),
    }


# Prompt template for LDS short-form content
# NOTE: All JSON braces are escaped with {{ }} for Python .format() compatibility
# Only {topic}, {topic_context}, {hook_question}, {duration_seconds}, {word_count} are placeholders
LDS_SCRIPT_PROMPT = """
{{
  "input_data": {{
    "topic": "{topic}",
    "topic_context": "{topic_context}",
    "hook_question": "{hook_question}"
  }},
  "instructions": {{
    "Task": "Act as the Executive Producer & Audio-Visual Director for LDS short-form content. Create a viral 9:16 vertical video script optimized for TikTok/Reels/Shorts using ElevenLabs V3.",
    "Goal": "Produce a script with a runtime of {duration_seconds} seconds (approximately {word_count} words). The content must be faith-promoting, doctrinally accurate, and emotionally engaging for an English-speaking international audience.",
    "Language": "ENGLISH ONLY. All dialogue, text overlays, and content must be in English for US and international English-speaking audiences.",
    "Audience": "English-speaking members of The Church of Jesus Christ of Latter-day Saints seeking spiritual growth, understanding, and community. Primary markets: United States, Canada, UK, Australia.",
    "Persona": {{
      "Character_A": {{
        "Name": "Analyst",
        "Role": "The Knowledgeable Scripture Scholar",
        "Traits": "Studies scriptures deeply and cites prophets with precision. Warm, faithful, reverent. Uses ElevenLabs emotion tags: [softly], [reverently], [with conviction], [warmly], [smiling], [deep breath], [whispers].",
        "Voice_Notes": "Professional female voice (Eve). Clear enunciation. Pacing should feel like a loving Sunday School teacher.",
        "Voice_ID": "BZgkqPqms7Kj9ulSkVzn"
      }},
      "Character_B": {{
        "Name": "Skeptic",
        "Role": "The Curious Learner",
        "Traits": "Represents members seeking to understand doctrine better. Asks sincere questions, humble curiosity. Uses ElevenLabs emotion tags: [curious], [thoughtfully], [surprised], [realizing], [pondering], [nervous laugh], [sighs].",
        "Voice_Notes": "Young male voice (Charles). Natural conversational tone. Occasional hesitation to show genuine seeking.",
        "Voice_ID": "S9GPGBaMND8XWwwzxQXp"
      }},
      "Viewer_Experience": "Parasocial Connection. The viewer feels their questions are validated and they receive clear, faith-affirming answers. They feel like they're eavesdropping on a meaningful gospel conversation.",
      "CRITICAL_NOTE": "Character names MUST be exactly 'Analyst' and 'Skeptic' in the dialogue JSON for correct voice mapping in audio generation."
    }},
    "Content_Guidelines": {{
      "Tone": "Always faith-promoting and positive about the Church",
      "Sources": "Only cite verified scriptures, prophet quotes, and official Church sources",
      "Accuracy": "Never contradict official Church doctrine",
      "Goal": "Build a faithful community, help members understand doctrine",
      "Relevance": "When connecting to current events, focus on eternal principles that transcend the news cycle"
    }},
    "Context": {{
      "Structure": "Start 'In Media Res' (mid-conversation). No intros or greetings. Jump straight into a compelling question or observation from Skeptic.",
      "Pacing": "Quick exchanges. Each response should be concise but impactful. Use ellipses '...' for natural pauses.",
      "Ending": "No goodbyes. End with a powerful testimony, scripture, or open reflection that invites the viewer to ponder and comment."
    }},
    "Format": {{
      "Text_Normalization": "Strictly NO DIGITS. Write '1830' as 'eighteen thirty', 'D&C 121' as 'Doctrine and Covenants section one twenty-one', '3 Nephi' as 'Third Nephi', '$50' as 'fifty dollars', '25%' as 'twenty-five percent'.",
      "Audio_Engineering": "ElevenLabs V3 optimization. Use emotion tags in brackets for natural delivery. Use ellipses '...' for pacing and pauses.",
      "Visual_Strategy": {{
        "Opening_Image": "FIRST frame must be a compelling visual that appears BEFORE any dialogue. This hooks the viewer.",
        "Hook_Text": "Display catchy title '{hook_question}' at the TOP of the video throughout as text overlay.",
        "Image_First_Rule": "Every visual_asset with an image_prompt should appear at the START of its corresponding dialogue line.",
        "Image_Style": "Clean professional Vector Illustrations. Modern LDS aesthetic. Do NOT include text like '4k' or 'resolution' in prompts."
      }},
      "Cinematography_Rules": {{
        "Requirement": "Every dialogue object MUST include a 'character_poses' array.",
        "Timing": "Use 'start_word_index' and 'end_word_index' (0-indexed) to map poses to specific parts of the sentence. You can switch poses mid-sentence to reflect tone shifts.",
        "Poses_Available": [
          {{ "id": "analyst_close", "character": "Analyst", "description": "Close-up. Sharing testimony, profound truths, whispering." }},
          {{ "id": "analyst_front", "character": "Analyst", "description": "Medium shot. Standard teaching, explaining doctrine, neutral." }},
          {{ "id": "analyst_pov", "character": "Analyst", "description": "POV shot from Skeptic perspective. Used when being asked a question." }},
          {{ "id": "skeptic_close", "character": "Skeptic", "description": "Close-up. Realization, emotion, confusion, nervous laughter." }},
          {{ "id": "skeptic_front", "character": "Skeptic", "description": "Medium shot. Asking questions, listening, general inquiries." }},
          {{ "id": "skeptic_side", "character": "Skeptic", "description": "Side profile. Thinking, reflecting, hesitation, avoiding eye contact." }}
        ]
      }},
      "Output_Structure": "Output ONLY valid JSON following the template below. No markdown text outside the JSON."
    }},
    "Output_JSON_Template": {{
      "script": {{
        "id": "unique_id_here",
        "topic": "topic_name_here",
        "hook_text": "Catchy question or statement for top overlay",
        "language": "en",
        "duration_target_seconds": 60,
        "opening_visual": {{
          "image_prompt": "Vector illustration: Compelling opening image that captures the theme. Modern clean style.",
          "duration_seconds": 3,
          "text_overlay": "Hook text appears here"
        }},
        "dialogue": [
          {{
            "character": "Skeptic",
            "text": "[curious] ...but I have always wondered, why does this matter so much?",
            "character_poses": [
              {{ "pose_id": "skeptic_front", "start_word_index": 0, "end_word_index": 6 }},
              {{ "pose_id": "skeptic_close", "start_word_index": 7, "end_word_index": 12 }}
            ],
            "visual_assets": null
          }},
          {{
            "character": "Analyst",
            "text": "[warmly] That is such a beautiful question... [softly] Let me share what President Nelson taught about this.",
            "character_poses": [
              {{ "pose_id": "analyst_front", "start_word_index": 0, "end_word_index": 7 }},
              {{ "pose_id": "analyst_close", "start_word_index": 8, "end_word_index": 17 }}
            ],
            "visual_assets": [
              {{
                "visual_asset_id": "1a",
                "image_prompt": "Vector illustration: President Russell M. Nelson speaking at General Conference podium. Clean modern style, warm lighting."
              }}
            ]
          }},
          {{
            "character": "Skeptic",
            "text": "[realizing] So it is not about... [thoughtfully] it is about who we become.",
            "character_poses": [
              {{ "pose_id": "skeptic_side", "start_word_index": 0, "end_word_index": 5 }},
              {{ "pose_id": "skeptic_close", "start_word_index": 6, "end_word_index": 11 }}
            ],
            "visual_assets": null
          }},
          {{
            "character": "Analyst",
            "text": "[with conviction] Exactly. [reverently] And that... that changes everything.",
            "character_poses": [
              {{ "pose_id": "analyst_front", "start_word_index": 0, "end_word_index": 2 }},
              {{ "pose_id": "analyst_close", "start_word_index": 3, "end_word_index": 7 }}
            ],
            "visual_assets": [
              {{
                "visual_asset_id": "2a",
                "image_prompt": "Vector illustration: Silhouette of person kneeling in prayer with soft light rays. Peaceful, contemplative mood."
              }}
            ]
          }}
        ],
        "call_to_action": "What do you think? Share your thoughts below.",
        "hashtags": ["#LDS", "#Faith", "#Testimony", "#PresidentNelson", "#GeneralConference"]
      }}
    }}
  }}
}}
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
        "language": "en",
        "language_note": "IMPORTANT: All content must be in ENGLISH for US/international audiences.",
        "parameters": {
            "topic": topic,
            "topic_context": topic_context,
            "hook_question": hook_question or f"What about {topic}?",
            "duration_seconds": duration_seconds,
            "word_count_target": word_count
        },
        "characters": {
            "analyst": {
                "name": "Analyst",
                "role": "The knowledgeable scripture scholar who cites prophets, scriptures, testimonies",
                "voice_id": "BZgkqPqms7Kj9ulSkVzn",
                "voice_name": "Eve (professional female)",
                "emotion_tags": ["[softly]", "[reverently]", "[with conviction]", "[warmly]", "[smiling]", "[deep breath]", "[whispers]"],
                "poses": ["analyst_close", "analyst_front", "analyst_pov"]
            },
            "skeptic": {
                "name": "Skeptic",
                "role": "The curious learner asking sincere questions",
                "voice_id": "S9GPGBaMND8XWwwzxQXp",
                "voice_name": "Charles (young male)",
                "emotion_tags": ["[curious]", "[thoughtfully]", "[surprised]", "[realizing]", "[pondering]", "[nervous laugh]", "[sighs]"],
                "poses": ["skeptic_close", "skeptic_front", "skeptic_side"]
            }
        },
        "character_note": "IMPORTANT: Use exactly 'Analyst' and 'Skeptic' as character names in the dialogue for correct voice mapping.",
        "generation_prompt": prompt,
        "instructions": """
IMPORTANT: Generate ALL content in ENGLISH only.

CRITICAL - CHARACTER NAMES FOR AUDIO:
- Use EXACTLY 'Analyst' for the scripture scholar (female voice - Eve)
- Use EXACTLY 'Skeptic' for the curious learner (male voice - Charles)
- These names MUST match exactly for correct audio generation!

To generate the script, Claude should:
1. Use the topic and context provided
2. Create a natural dialogue between Analyst and Skeptic
3. Include accurate scripture references and prophet quotes
4. Format the output as valid JSON matching the template in generation_prompt
5. Include ElevenLabs emotion tags: [warmly], [reverently], [curious], [softly], [with conviction], etc.
6. Use ellipses '...' for natural pauses in speech
7. Assign appropriate character poses to each dialogue line with word indices
8. Include visual_assets with image_prompts for key moments
9. Add an opening_visual that appears BEFORE dialogue starts
10. Create a catchy hook_text that displays at the TOP of the video

Output Format Requirements:
- Start 'In Media Res' - no intros or greetings
- End with reflection - no goodbyes
- NO DIGITS - write numbers as words (e.g., 'eighteen thirty' not '1830')
- Include opening_visual with image_prompt and hook text overlay
- Each dialogue line needs character_poses array with pose_id and word indices
- Character names in dialogue MUST be 'Analyst' or 'Skeptic' exactly

After generation, save the script to: data/shorts/scripts/{script_id}.json
""",
        "available_poses": {
            "analyst": ["analyst_close", "analyst_front", "analyst_pov"],
            "skeptic": ["skeptic_close", "skeptic_front", "skeptic_side"]
        },
        "visual_requirements": {
            "opening_visual": "REQUIRED - First frame before dialogue with hook text overlay",
            "image_style": "Clean professional Vector Illustrations. Modern LDS aesthetic.",
            "image_rules": [
                "Do NOT include '4k' or 'resolution' text in image prompts",
                "Images appear at START of corresponding dialogue line",
                "Use images for key moments: scripture references, prophet quotes, emotional peaks"
            ]
        },
        "floating_image_scheduling": {
            "overview": "Floating images appear with blur background effect during video playback",
            "timing_rules": {
                "interval": "Place images every 15-20 seconds for optimal engagement",
                "skip_start": "No images in first 5 seconds",
                "skip_end": "No images in last 5 seconds",
                "display_duration": "Each image shows for 5 seconds"
            },
            "placement_priorities": [
                "Scripture references or quotes",
                "Prophet mentions or teachings",
                "Key doctrinal points",
                "Emotional peaks or realizations"
            ],
            "calculation": f"For a {duration_seconds} second video, include approximately {max(1, duration_seconds // 17)} floating images"
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


def validate_script_poses(script_data: dict) -> dict:
    """
    Validate that all poses in a script are valid standard poses.

    Returns:
        dict: Validation result with any issues found
    """
    issues = []
    valid_poses = set(STANDARD_POSES.keys())

    dialogue = script_data.get("script", {}).get("dialogue", [])
    if not dialogue:
        dialogue = script_data.get("dialogue", [])

    for idx, line in enumerate(dialogue):
        character = line.get("character", "")
        poses = line.get("character_poses", [])

        # Validate character name
        if character not in ["Analyst", "Skeptic"]:
            issues.append(f"Line {idx}: Invalid character '{character}'. Must be 'Analyst' or 'Skeptic'.")

        # Validate poses
        char_key = character.lower() if character in ["Analyst", "Skeptic"] else "analyst"
        valid_char_poses = [p for p in valid_poses if p.startswith(char_key)]

        for pose_entry in poses:
            pose_id = pose_entry.get("pose_id", "")
            if pose_id not in valid_poses:
                issues.append(f"Line {idx}: Invalid pose_id '{pose_id}'. Valid poses: {valid_char_poses}")
            elif not pose_id.startswith(char_key):
                issues.append(f"Line {idx}: Pose '{pose_id}' doesn't match character '{character}'.")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "valid_poses": list(valid_poses)
    }


def get_pose_info() -> dict:
    """
    Get information about all available poses for script generation.

    Returns:
        dict: Pose information organized by character
    """
    return {
        "analyst": {
            "character_name": "Analyst",
            "default_pose": "analyst_front",
            "poses": {
                "analyst_close": {
                    "description": "Close-up portrait. Use for testimony, profound truths, whispers.",
                    "emotion_triggers": ["[softly]", "[whispers]", "[reverently]", "[with conviction]"]
                },
                "analyst_front": {
                    "description": "Medium shot facing viewer. Default for teaching and explaining.",
                    "emotion_triggers": ["[warmly]", "[smiling]", "default"]
                },
                "analyst_pov": {
                    "description": "POV from Skeptic's view. Use when being asked a question.",
                    "emotion_triggers": ["listening", "responding", "[deep breath]"]
                }
            }
        },
        "skeptic": {
            "character_name": "Skeptic",
            "default_pose": "skeptic_front",
            "poses": {
                "skeptic_close": {
                    "description": "Close-up. Use for realization, strong emotion, confusion.",
                    "emotion_triggers": ["[realizing]", "[surprised]", "[nervous laugh]"]
                },
                "skeptic_front": {
                    "description": "Medium shot facing viewer. Default for asking questions.",
                    "emotion_triggers": ["[curious]", "asking", "default"]
                },
                "skeptic_side": {
                    "description": "Side profile. Use for thinking, reflecting, hesitation.",
                    "emotion_triggers": ["[thoughtfully]", "[pondering]", "[sighs]"]
                }
            }
        }
    }


def suggest_pose_for_text(character: str, text: str) -> str:
    """
    Suggest an appropriate pose based on character and dialogue text.

    Args:
        character: "Analyst" or "Skeptic"
        text: The dialogue text (with emotion tags)

    Returns:
        str: Suggested pose_id
    """
    char_key = character.lower()
    text_lower = text.lower()

    # Analyst poses
    if char_key == "analyst":
        if any(tag in text_lower for tag in ["[softly]", "[whispers]", "[reverently]", "[with conviction]"]):
            return "analyst_close"
        elif any(tag in text_lower for tag in ["[deep breath]", "listening"]):
            return "analyst_pov"
        else:
            return "analyst_front"

    # Skeptic poses
    elif char_key == "skeptic":
        if any(tag in text_lower for tag in ["[realizing]", "[surprised]", "[nervous laugh]"]):
            return "skeptic_close"
        elif any(tag in text_lower for tag in ["[thoughtfully]", "[pondering]", "[sighs]"]):
            return "skeptic_side"
        else:
            return "skeptic_front"

    # Fallback
    return f"{char_key}_front"


def add_intelligent_image_scheduling(
    script_data: dict,
    min_interval_seconds: float = 15.0,
    max_interval_seconds: float = 20.0,
    words_per_second: float = 2.5
) -> dict:
    """
    Add intelligent image scheduling to a script's visual_assets.

    This ensures images are distributed evenly throughout the video,
    appearing approximately every 15-20 seconds for optimal engagement.

    Args:
        script_data: The script JSON with dialogue
        min_interval_seconds: Minimum seconds between floating images
        max_interval_seconds: Maximum seconds between floating images
        words_per_second: Average speaking rate (default 2.5 words/sec)

    Returns:
        dict: Updated script with visual_assets properly scheduled
    """
    script = script_data.get("script", script_data)
    dialogue = script.get("dialogue", [])

    if not dialogue:
        return script_data

    # Calculate word counts and estimated timestamps for each line
    cumulative_words = 0
    dialogue_timings = []

    for idx, line in enumerate(dialogue):
        text = line.get("text", "")
        # Count words (excluding emotion tags)
        import re
        clean_text = re.sub(r'\[.*?\]', '', text)
        word_count = len(clean_text.split())

        start_time = cumulative_words / words_per_second
        end_time = (cumulative_words + word_count) / words_per_second

        dialogue_timings.append({
            "index": idx,
            "start_time": start_time,
            "end_time": end_time,
            "word_count": word_count,
            "has_visual": line.get("visual_assets") is not None and len(line.get("visual_assets", [])) > 0
        })

        cumulative_words += word_count

    total_duration = cumulative_words / words_per_second

    # Calculate ideal image intervals
    avg_interval = (min_interval_seconds + max_interval_seconds) / 2
    num_images_needed = max(1, int(total_duration / avg_interval))

    # Find existing images
    existing_image_indices = [
        t["index"] for t in dialogue_timings if t["has_visual"]
    ]

    # If we already have enough well-distributed images, return as is
    if len(existing_image_indices) >= num_images_needed:
        return script_data

    # Calculate ideal timestamps for images
    ideal_timestamps = []
    for i in range(num_images_needed):
        # Start at 5 seconds, end 5 seconds before end
        available_window = total_duration - 10
        if available_window > 0:
            timestamp = 5 + (available_window / (num_images_needed + 1)) * (i + 1)
            ideal_timestamps.append(timestamp)

    # Find best dialogue lines for each ideal timestamp
    suggested_image_lines = []
    for ideal_time in ideal_timestamps:
        # Find the dialogue line closest to this timestamp
        best_idx = None
        best_distance = float('inf')

        for timing in dialogue_timings:
            # Prefer lines that don't already have images
            if timing["index"] in existing_image_indices:
                continue
            if timing["index"] in suggested_image_lines:
                continue

            # Calculate distance to ideal time
            line_midpoint = (timing["start_time"] + timing["end_time"]) / 2
            distance = abs(line_midpoint - ideal_time)

            if distance < best_distance:
                best_distance = distance
                best_idx = timing["index"]

        if best_idx is not None:
            suggested_image_lines.append(best_idx)

    # Add scheduling info to script
    script_data["image_scheduling"] = {
        "total_duration_estimate": total_duration,
        "images_recommended": num_images_needed,
        "existing_images_at_lines": existing_image_indices,
        "suggested_add_images_at_lines": suggested_image_lines,
        "interval_config": {
            "min_seconds": min_interval_seconds,
            "max_seconds": max_interval_seconds
        },
        "instructions": f"""
To achieve optimal image pacing (every {min_interval_seconds}-{max_interval_seconds} seconds):

Current images at dialogue lines: {existing_image_indices}
Suggested lines to ADD images: {suggested_image_lines}

For each suggested line, add a visual_assets array with:
{{
  "visual_asset_id": "auto_X",
  "image_prompt": "Vector illustration: [describe relevant scene]. Modern LDS aesthetic."
}}

This will create a floating image effect with blur background during render.
"""
    }

    return script_data


def calculate_visual_asset_timing(
    dialogue: list,
    words_per_second: float = 2.5
) -> list:
    """
    Calculate when each visual asset should appear based on dialogue timing.

    Args:
        dialogue: List of dialogue lines
        words_per_second: Average speaking rate

    Returns:
        list: Visual asset timings with start/end times
    """
    import re

    visual_timings = []
    cumulative_words = 0

    for idx, line in enumerate(dialogue):
        text = line.get("text", "")
        clean_text = re.sub(r'\[.*?\]', '', text)
        word_count = len(clean_text.split())

        start_time = cumulative_words / words_per_second

        visual_assets = line.get("visual_assets", [])
        if visual_assets:
            for asset in visual_assets:
                visual_timings.append({
                    "dialogue_index": idx,
                    "visual_asset_id": asset.get("visual_asset_id", f"asset_{idx}"),
                    "image_prompt": asset.get("image_prompt", ""),
                    "path": asset.get("path", ""),
                    "start_time": start_time,
                    "description": asset.get("description", asset.get("image_prompt", ""))
                })

        cumulative_words += word_count

    return visual_timings


def get_image_scheduling_guidelines() -> dict:
    """
    Get guidelines for intelligent image placement in scripts.

    Returns:
        dict: Guidelines and best practices for image scheduling
    """
    return {
        "overview": """
Floating images create visual interest and emphasize key points in LDS short videos.
For optimal engagement, images should appear every 15-20 seconds.
""",
        "timing_rules": {
            "minimum_interval": "15 seconds between images",
            "maximum_interval": "20 seconds between images",
            "skip_first": "5 seconds (let dialogue establish)",
            "skip_last": "5 seconds (clean ending)",
            "display_duration": "5 seconds per image"
        },
        "placement_priorities": [
            "Scripture references or quotes",
            "Prophet mentions or teachings",
            "Key doctrinal points",
            "Emotional peaks or realizations",
            "Transition moments between topics"
        ],
        "image_prompt_guidelines": {
            "style": "Clean professional Vector Illustrations. Modern LDS aesthetic.",
            "avoid": ["'4k'", "'resolution'", "realistic photos", "copyrighted imagery"],
            "include": ["relevant symbols", "emotions", "gospel themes", "clean composition"]
        },
        "example_prompts": [
            "Vector illustration: Open scriptures with soft light rays. Clean modern style.",
            "Vector illustration: Temple silhouette at sunset. Peaceful, contemplative.",
            "Vector illustration: Family gathered around scriptures. Warm tones.",
            "Vector illustration: Person kneeling in prayer. Soft gradient background."
        ]
    }
