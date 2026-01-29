# Zero-Sum LDS - Short-Form Video Creator

An MCP (Model Context Protocol) server that automates short-form video creation for LDS (Latter-day Saints) content. Produces 9:16 vertical videos optimized for TikTok, Instagram Reels, and YouTube Shorts.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Complete Workflow](#complete-workflow)
- [Manual Image Management](#manual-image-management)
- [Available MCP Tools](#available-mcp-tools)
- [Script Format](#script-format)
- [Character System](#character-system)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

Zero-Sum LDS creates professional short-form videos featuring two characters having meaningful gospel conversations:

- **Analyst** (Female): Knowledgeable scripture scholar who cites prophets and scriptures
- **Skeptic** (Male): Curious learner asking questions and seeking understanding

### Features

- ✅ Automated script generation with verified LDS content
- ✅ Professional voice narration using ElevenLabs
- ✅ Lip-sync animation with syllable detection
- ✅ Word-by-word captions
- ✅ Floating image support with custom timing
- ✅ Background rendering with progress tracking
- ✅ Project lifecycle management

---

## Quick Start

### 1. Check Current Status
```
Tool: get_status
```
This shows your current project state and next recommended actions.

### 2. Create a New Project
```
Tool: workflow
Parameters:
  - operation: "create_project"
  - topic: "Finding Peace in Troubled Times"
```

### 3. Generate Script
```
Tool: create_script
Parameters:
  - topic: "Finding Peace in Troubled Times"
  - hook_question: "How do you find peace?"
  - duration_seconds: 75
```

### 4. Save the Script
After Claude generates the script JSON, save it:
```
Tool: save_script
Parameters:
  - script_json: { "script": { ... } }
```

### 5. Generate Audio
```
Tool: generate_audio
Parameters:
  - script_id: "lds_YYYYMMDD_HHMMSS_xxxxxx"
```

### 6. Add Images (Optional)
Place images in `data/shorts/images/` and update the registry. See [Manual Image Management](#manual-image-management).

### 7. Render Video
```
Tool: execute_render
Parameters:
  - script_id: "lds_YYYYMMDD_HHMMSS_xxxxxx"
  - hook_text: "How do you find peace?"
```

### 8. Check Progress
```
Tool: check_render_status
```

---

## Complete Workflow

### Phase 1: Research & Planning

1. **Search for LDS Content**
   ```
   Tool: search_lds_content
   Parameters:
     - query: "peace in troubled times"
     - source_type: "all"  # Options: scriptures, conference, liahona, all
   ```

2. **Verify Quotes** (Important!)
   ```
   Tool: verify_quote
   Parameters:
     - quote: "The exact quote text"
     - attributed_to: "Elder David A. Bednar"
     - source: "April 2024 General Conference"
   ```

### Phase 2: Script Creation

1. **Generate Script Template**
   ```
   Tool: create_script
   Parameters:
     - topic: "Your topic"
     - topic_context: "Include verified quotes and scriptures here"
     - hook_question: "Short catchy question (3-5 words)"
     - duration_seconds: 75  # Recommended: 60-90 seconds
   ```

2. **Save the Generated Script**
   ```
   Tool: save_script
   Parameters:
     - script_json: { complete script JSON from Claude }
   ```

### Phase 3: Audio Generation

```
Tool: generate_audio
Parameters:
  - script_id: "your_project_id"
```

This creates:
- `data/shorts/audio/{script_id}.mp3` - The audio file
- `data/shorts/audio/{script_id}_timestamps.json` - Word-level timing

### Phase 4: Image Management

See [Manual Image Management](#manual-image-management) section below.

### Phase 5: Rendering

1. **Start the Render**
   ```
   Tool: execute_render
   Parameters:
     - script_id: "your_project_id"
     - hook_text: "Your hook question"
     - output_filename: "my_video"  # Optional, defaults to script_id
   ```

2. **Monitor Progress**
   ```
   Tool: check_render_status
   ```

3. **View Logs if Needed**
   ```
   Tool: get_render_log
   Parameters:
     - tail_lines: 50
   ```

### Phase 6: Completion

1. **Find Your Video**
   - Location: `data/shorts/output/{output_filename}.mp4`
   - Format: 1080x1920 (9:16 vertical)

2. **Archive the Project**
   ```
   Tool: archive_project
   ```

3. **Start Fresh**
   ```
   Tool: cleanup_workspace
   Parameters:
     - confirm: true
     - archive_first: true
   ```

---

## Manual Image Management

### Important: MCP Cannot Receive Images from Chat

The MCP protocol only accepts text inputs. You must manually place images in the project folder and register them.

### Step-by-Step Image Setup

#### 1. Place Images in the Folder

Copy your images to:
```
data/shorts/images/
```

#### 2. Naming Convention (Recommended)

Use simple numeric names for automatic matching:
```
1.jpeg  →  maps to visual_asset_id "1a"
2.jpeg  →  maps to visual_asset_id "2a"
3.png   →  maps to visual_asset_id "3a"
4.jpeg  →  maps to visual_asset_id "4a"
...
```

The renderer will automatically find images by number.

#### 3. Alternative: Update the Image Registry

For custom filenames, edit `data/shorts/images/image_registry.json`:

```json
{
  "images": [
    {
      "visual_asset_id": "1a",
      "path": "C:/path/to/project/data/shorts/images/elder_bednar.jpeg",
      "description": "Elder Bednar at General Conference"
    },
    {
      "visual_asset_id": "2a",
      "path": "C:/path/to/project/data/shorts/images/scripture_quote.png",
      "description": "Scripture quote from D&C"
    }
  ]
}
```

#### 4. How Images Appear in the Video

Images appear at the **midpoint** of the dialogue segment they're assigned to:

```
Timeline for a dialogue line:
|-------- First Half --------|-------- Second Half --------|
     [Character Speaking]          [Image Appears]
```

**Special Case: Opening Visual**

The `opening_visual` in your script works differently:
- Shows from the **start** of the video
- Character is already speaking (audio plays)
- Fades out at the **midpoint** of the first dialogue
- Then the character becomes visible

### Using manage_files Tool

You can also use MCP to copy images from other locations:

```
Tool: manage_files
Parameters:
  - operation: "copy"
  - source: "C:/Users/you/Downloads/my_image.jpeg"
  - destination: "data/shorts/images/1.jpeg"
```

Or register multiple images at once:

```
Tool: manage_files
Parameters:
  - operation: "register_images"
  - image_paths: ["C:/path/to/img1.jpeg", "C:/path/to/img2.png"]
  - project_id: "your_project_id"
```

---

## Available MCP Tools

### Content & Research

| Tool | Description |
|------|-------------|
| `search_lds_content` | Search scriptures, prophet quotes, conference talks |
| `search_world_news` | Find current events with gospel connections |
| `verify_quote` | Verify accuracy of quotes before using them |

### Script & Project

| Tool | Description |
|------|-------------|
| `create_script` | Generate a script template for a topic |
| `save_script` | Save script JSON to disk |
| `get_status` | Check current project state |
| `get_project_status` | Detailed status of specific project |
| `list_projects` | List all projects |
| `workflow` | High-level operations (create_project, finalize_script, etc.) |

### Media

| Tool | Description |
|------|-------------|
| `generate_audio` | Create voice narration with ElevenLabs |
| `upload_images` | Register images for the video |
| `manage_files` | Copy, move, list files in project |

### Rendering

| Tool | Description |
|------|-------------|
| `render_short` | Validate and prepare render plan |
| `execute_render` | Start the actual video render |
| `check_render_status` | Monitor render progress |
| `get_render_log` | View render logs |

### Lifecycle

| Tool | Description |
|------|-------------|
| `archive_project` | Move completed project to archive |
| `cleanup_workspace` | Reset workspace for new project |
| `list_archived` | Show archived projects |

---

## Script Format

### Required Structure

```json
{
  "script": {
    "id": "lds_20260128_120000_abc123",
    "topic": "Finding Peace in Troubled Times",
    "hook_text": "How do you find peace?",
    "language": "en",
    "duration_target_seconds": 75,
    "sources": [
      {
        "talk": "Be Still, and Know That I Am God",
        "speaker": "Elder David A. Bednar",
        "date": "April 2024 General Conference"
      }
    ],
    "verified_quotes": [
      {
        "quote": "The exact quote text...",
        "source": "Speaker, Date",
        "verified": true
      }
    ],
    "opening_visual": {
      "image_prompt": "Vector illustration: Description...",
      "duration_seconds": 3,
      "text_overlay": "How do you find peace?"
    },
    "dialogue": [
      {
        "character": "Skeptic",
        "text": "[sighs] ...with everything happening in the world...",
        "character_poses": [
          { "pose_id": "skeptic_side", "start_word_index": 0, "end_word_index": 5 }
        ],
        "visual_assets": null
      },
      {
        "character": "Analyst",
        "text": "[warmly] That is exactly what Elder Bednar addressed...",
        "character_poses": [
          { "pose_id": "analyst_front", "start_word_index": 0, "end_word_index": 8 }
        ],
        "visual_assets": [
          {
            "visual_asset_id": "1a",
            "image_prompt": "Vector illustration: Elder Bednar speaking..."
          }
        ]
      }
    ],
    "call_to_action": "Where do you find your peace? Comment below.",
    "hashtags": ["#LDS", "#FindPeace", "#GeneralConference"]
  }
}
```

### Emotion Tags

Include emotion tags in dialogue text for natural speech:

**Analyst (Female):**
- `[softly]` - Gentle, quiet delivery
- `[reverently]` - Sacred, spiritual tone
- `[warmly]` - Friendly, inviting
- `[with conviction]` - Strong testimony
- `[deep breath]` - Pause for emphasis

**Skeptic (Male):**
- `[curious]` - Questioning, interested
- `[thoughtfully]` - Reflective
- `[sighs]` - Contemplative pause
- `[realizing]` - Moment of understanding
- `[pondering]` - Deep thought

---

## Character System

### Available Characters

| Character | Voice | Role |
|-----------|-------|------|
| **Analyst** | Eve (Female) | Scripture scholar, shares doctrine |
| **Skeptic** | Charles (Male) | Curious learner, asks questions |

### Character Poses

Each character has 3 poses with open/closed mouth variants for lip-sync:

**Analyst Poses:**
| Pose ID | Type | Best For |
|---------|------|----------|
| `analyst_front` | Medium shot | Teaching, explaining (DEFAULT) |
| `analyst_close` | Close-up | Testimony, profound truths |
| `analyst_pov` | POV shot | Responding to questions |

**Skeptic Poses:**
| Pose ID | Type | Best For |
|---------|------|----------|
| `skeptic_front` | Medium shot | Asking questions (DEFAULT) |
| `skeptic_close` | Close-up | Realization, emotion |
| `skeptic_side` | Side profile | Thinking, reflecting |

### Pose Switching

Specify poses in your script:

```json
"character_poses": [
  { "pose_id": "skeptic_side", "start_word_index": 0, "end_word_index": 3 },
  { "pose_id": "skeptic_close", "start_word_index": 4, "end_word_index": 14 }
]
```

---

## File Structure

```
zero-sum-yt/
├── lds_mcp/
│   ├── lds_server.py           # Main MCP server
│   └── tools/                  # All MCP tool implementations
│
├── src/
│   ├── core/
│   │   ├── elevenlabs.py       # ElevenLabs voice generation
│   │   └── video_renderer.py   # FFmpeg/PyAV video rendering
│   └── handlers/
│       └── video_handler.py    # Video processing handlers
│
├── data/
│   ├── shorts/
│   │   ├── scripts/            # Project scripts (JSON)
│   │   ├── audio/              # Generated audio (MP3) + timestamps
│   │   ├── images/             # Visual assets for videos
│   │   │   └── image_registry.json  # Image ID → path mapping
│   │   └── output/             # Final rendered videos (MP4)
│   │
│   ├── images/
│   │   ├── images_catalog.json # Character pose definitions
│   │   ├── analyst/            # Analyst character images
│   │   └── skeptic/            # Skeptic character images
│   │
│   ├── audio/
│   │   ├── music/              # Background music files
│   │   └── sound_effect/       # Sound effect files
│   │
│   ├── font/                   # Fonts for captions
│   │
│   └── production_plan.json    # Legacy script copy
│
├── old-videos/                 # Archived projects
│
├── .env                        # Environment variables (API keys)
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── claude_desktop_config.json  # MCP server configuration
└── README.md                   # This file
```

### Naming Conventions

**Project IDs:** `lds_{YYYYMMDD}_{HHMMSS}_{random}`
- Example: `lds_20260128_120000_abc123`

**Files per Project:**
- Script: `data/shorts/scripts/{project_id}.json`
- Audio: `data/shorts/audio/{project_id}.mp3`
- Timestamps: `data/shorts/audio/{project_id}_timestamps.json`
- Video: `data/shorts/output/{project_id}.mp4`

---

## Configuration

### Claude Desktop Config

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zero-sum-lds": {
      "command": "python",
      "args": ["path/to/zero-sum-yt/lds_mcp/lds_server.py"],
      "env": {
        "ELEVEN_LABS_API_KEY2": "your_elevenlabs_key"
      }
    }
  }
}
```

### Video Output Settings

- **Resolution:** 1080 x 1920 (9:16 vertical)
- **Frame Rate:** 30 FPS
- **Format:** MP4 (H.264)
- **Background:** Dark (RGB: 15, 15, 20)

---

## Troubleshooting

### Images Not Appearing

1. **Check the image registry:**
   - Verify `data/shorts/images/image_registry.json` has correct paths
   - Paths must be absolute (full path from root)

2. **Check image naming:**
   - Use numeric names (`1.jpeg`, `2.png`) for automatic matching
   - Or update the registry with custom names

3. **Verify images exist:**
   ```
   Tool: manage_files
   Parameters:
     - operation: "list"
     - path: "data/shorts/images"
   ```

### Audio Generation Fails

1. Check your ElevenLabs API key is set
2. Verify the script has valid character names (`Analyst` or `Skeptic`)
3. Check you have API credits remaining

### Render Fails

1. **Check logs:**
   ```
   Tool: get_render_log
   ```

2. **Verify prerequisites:**
   - Script exists in `data/shorts/scripts/`
   - Audio exists in `data/shorts/audio/`
   - Timestamps JSON exists

3. **Check character images:**
   - Verify `data/images/analyst/` and `data/images/skeptic/` have all pose images

### Project State Issues

Reset the workspace:
```
Tool: cleanup_workspace
Parameters:
  - confirm: true
  - archive_first: true
```

---

## Support

For issues or feature requests, please open an issue on the repository.

---

*Created with Claude Code*
