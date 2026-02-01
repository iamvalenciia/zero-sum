# Zero-Sum LDS - Automated Video Production

## 🚀 Quick Start Workflow

### 1. Generate Script
Copy the [Standardized Prompt](#-standardized-prompt-for-script-generation) below and paste it into your LLM (Claude/ChatGPT).
Save the resulting JSON as `data/shorts/scripts/your_script_name.json`.

### 2. Generate Audio
Run the audio generator:
```cmd
python generate_audio.py data/shorts/scripts/your_script_name.json
```
This creates: `data/shorts/audio/your_script_name.mp3`

### 3. Setup Images (Manual Step)
1. Go to `data/shorts/images/`.
2. Delete old images if starting fresh.
3. Paste your new images here.
4. **Naming Convention**: 
   - Rename images to match the `visual_asset_id` in your script (e.g., `1a.jpg`, `2a.png`, `3a.jpg`).
   - The system automatically finds `1a`, `2a`, etc., regardless of extension.

### 4. Render Video
**For Shorts (9:16 Vertical):**
```cmd
python render_short.py your_script_name --hook "Your Hook Text Here"
```
*Note: Timestamps are generated automatically using Whisper if they don't exist.*

**For Long Form / Widescreen:**
```cmd
python render_long.py your_script_name --hook "Title Here"
```

---

## 📋 Standardized Prompt for Script Generation

**Copy and paste the following prompt into your LLM to generate a compatible script:**

```markdown
Role: You are an expert LDS content creator specializing in engaging, faith-promoting short-form videos.

Task: Create a JSON script for a video conversation between two characters: "Analyst" (LDS Scholar) and "Skeptic" (Inquisitive Learner).

Requirements:
1.  **Format**: Return ONLY valid JSON matching the schema below. No markdown formatting around the JSON.
2.  **Characters**:
    *   **Analyst** (Female): Knowledgeable, references scriptures/prophets. Voice ID: (System Default)
    *   **Skeptic** (Male): Asks questions, reflects common struggles. Voice ID: (System Default)
3.  **Tone**: Insightful, peaceful, modern.
4.  **Duration**: 60-90 seconds.
5.  **Visuals**: Include `visual_assets` for key moments (images 1a, 2a, 3a...).
6.  **Poses**: Use ONLY these pose IDs:
    *   Analyst: `analyst_front`, `analyst_close`, `analyst_pov`
    *   Skeptic: `skeptic_front`, `skeptic_close`, `skeptic_side`
7.  **Emotions**: Include tags in text like `[warmly]`, `[curious]`, `[softly]`.

JSON Schema:
{
  "script": {
    "id": "lds_TOPIC_DATE",
    "topic": "Topic Description",
    "hook_text": "Short Hook Question?",
    "language": "en",
    "duration_target_seconds": 75,
    "opening_visual": {
      "image_prompt": "Description of opening image...",
      "duration_seconds": 3,
      "text_overlay": "Hook Text Overlay"
    },
    "dialogue": [
      {
        "character": "Skeptic",
        "text": "[sighs] Start with a problem or question...",
        "character_poses": [
          { "pose_id": "skeptic_side", "start_word_index": 0, "end_word_index": 10 }
        ],
        "visual_assets": null
      },
      {
        "character": "Analyst",
        "text": "[warmly] Respond with doctrine. As Elder Bednar said...",
        "character_poses": [
          { "pose_id": "analyst_front", "start_word_index": 0, "end_word_index": 15 }
        ],
        "visual_assets": [
          {
            "visual_asset_id": "1a",
            "start_word_index": 5,
            "end_word_index": 15,
            "image_prompt": "Description of image 1a..."
          }
        ]
      }
    ],
    "call_to_action": "Comment below...",
    "hashtags": ["#LDS", "#Faith"]
  }
}
```

---

## 🛠 Project Structure

- `data/shorts/scripts/`: Place JSON scripts here.
- `data/shorts/images/`: Place matching images here (1a.jpg, 2a.png).
- `data/shorts/audio/`: Generated audio files appear here.
- `data/shorts/output/`: Final rendered videos appear here.

## 📝 Commands Reference

| Task | Command |
|------|---------|
| **Generate Audio** | `python generate_audio.py <script_json_path>` |
| **Render Short** | `python render_short.py <script_id> --hook "Text"` |
| **Render Long** | `python render_long.py <script_id>` |
| **Help** | `python render_short.py --help` |

## 💡 Tips

- **Images**: If your script calls for `visual_asset_id": "1a"`, make sure you have a file named `1a.jpg` (or png/jpeg) in the images folder.
- **Audio Issues**: If audio fails, check your ElevenLabs API key in `.env`.
- **Character Poses**: The renderer tries to match character emotion to poses, but explicit `character_poses` in the script take precedence.
