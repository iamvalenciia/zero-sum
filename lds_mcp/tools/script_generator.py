"""
Script Generator for LDS Short-Form Content
Creates dialogue scripts featuring Analyst (knowledgeable) and Skeptic (curious learner).
Character names match ElevenLabs voice mapping for correct audio generation.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path


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
